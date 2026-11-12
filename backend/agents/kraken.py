"""Kraken Spot REST adapter.

Public market data uses Kraken's unauthenticated REST endpoints. Private
account reads are opt-in and require server-side credentials. Order placement
is intentionally unavailable until the independent risk and execution
subsystems have passed review.
"""
import base64
import hashlib
import hmac
import os
import time
from typing import Dict, List
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv

load_dotenv()

KRAKEN_API_BASE = "https://api.kraken.com/0"
YAHOO_FINANCE_BASES = (
    "https://query1.finance.yahoo.com/v8/finance/chart",
    "https://query2.finance.yahoo.com/v8/finance/chart",
)

GLOBAL_MACRO_SYMBOL_MAP: Dict[str, str] = {
    # Precious & Industrial Metals
    "XAU/USD": "GC=F",
    "XAG/USD": "SI=F",
    "XPT/USD": "PL=F",
    "XCU/USD": "HG=F",
    # Global Equity Indices
    "SPX500/USD": "^GSPC",
    "NAS100/USD": "^NDX",
    "US30/USD": "^DJI",
    "UK100/USD": "^FTSE",
    "GER40/USD": "^GDAXI",
    "JPN225/USD": "^N225",
}


class KrakenAgent:
    def __init__(self):
        self.api_key = os.getenv("KRAKEN_API_KEY")
        self.api_secret = os.getenv("KRAKEN_API_SECRET")
        self.account_reads_enabled = os.getenv("KRAKEN_ACCOUNT_READS_ENABLED", "false").lower() == "true"

    async def _public_request(self, endpoint: str, params: Dict[str, str]) -> Dict:
        url = f"{KRAKEN_API_BASE}/public/{endpoint}"
        # Use Kraken's display-name asset version so BTC/USD is stable in
        # API responses instead of requiring legacy XXBTZUSD pair identifiers.
        request_params = {**params, "assetVersion": "1"}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=4.0)) as client:
                response = await client.get(url, params=request_params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError("Kraken public market-data request failed.") from exc

        errors = payload.get("error", [])
        if errors:
            raise RuntimeError("Kraken rejected the market-data request.")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("Kraken returned an invalid market-data response.")
        return result

    async def get_asset_pairs(self) -> Dict:
        """Return Kraken's public spot-pair metadata for instrument discovery."""
        return await self._public_request("AssetPairs", {})

    def _private_signature(self, path: str, nonce: str, form_data: str) -> str:
        if not self.api_secret:
            raise RuntimeError("Kraken API secret is not configured.")

        try:
            secret = base64.b64decode(self.api_secret, validate=True)
        except Exception as exc:
            raise RuntimeError("Kraken API secret has an invalid encoding.") from exc

        digest = hashlib.sha256((nonce + form_data).encode("utf-8")).digest()
        message = path.encode("utf-8") + digest
        signature = hmac.new(secret, message, hashlib.sha512).digest()
        return base64.b64encode(signature).decode("ascii")

    async def _private_request(self, endpoint: str, params: Dict[str, str] | None = None) -> Dict:
        if not self.account_reads_enabled:
            raise RuntimeError("Kraken account reads are disabled until credentials are rotated and verified.")
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Kraken account credentials are not configured.")

        path = f"/0/private/{endpoint}"
        nonce = str(time.time_ns())
        payload = {"nonce": nonce, **(params or {})}
        form_data = urlencode(payload)
        signature = self._private_signature(path, nonce, form_data)

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=4.0)) as client:
                response = await client.post(
                    f"{KRAKEN_API_BASE}/private/{endpoint}",
                    content=form_data,
                    headers={
                        "API-Key": self.api_key,
                        "API-Sign": signature,
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                response.raise_for_status()
                result = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError("Kraken private account request failed.") from exc

        if result.get("error"):
            raise RuntimeError("Kraken rejected the private account request.")
        data = result.get("result")
        if not isinstance(data, dict):
            raise RuntimeError("Kraken returned an invalid private account response.")
        return data

    async def _yahoo_chart_request(self, yahoo_symbol: str, interval: str = "60m", range_str: str = "1mo") -> Dict:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        last_exc: Exception | None = None
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=4.0), headers=headers) as client:
            for base in YAHOO_FINANCE_BASES:
                try:
                    response = await client.get(
                        f"{base}/{yahoo_symbol}",
                        params={"interval": interval, "range": range_str},
                    )
                    response.raise_for_status()
                    payload = response.json()
                    results = payload.get("chart", {}).get("result")
                    if isinstance(results, list) and results and isinstance(results[0], dict):
                        return results[0]
                except Exception as exc:
                    last_exc = exc
        raise RuntimeError(f"Global macro market-data request failed for {yahoo_symbol}.") from last_exc

    async def _get_macro_ticker(self, pair: str, yahoo_symbol: str) -> Dict:
        chart = await self._yahoo_chart_request(yahoo_symbol, interval="60m", range_str="5d")
        meta = chart.get("meta") or {}
        quote = ((chart.get("indicators") or {}).get("quote") or [{}])[0]
        closes = [float(x) for x in (quote.get("close") or []) if x is not None and float(x) > 0]
        highs = [float(x) for x in (quote.get("high") or []) if x is not None and float(x) > 0]
        lows = [float(x) for x in (quote.get("low") or []) if x is not None and float(x) > 0]
        vols = [float(x) for x in (quote.get("volume") or []) if x is not None and float(x) >= 0]

        last_price = float(meta.get("regularMarketPrice") or (closes[-1] if closes else 0.0))
        if last_price <= 0:
            raise RuntimeError(f"Incomplete market price returned for {pair}.")

        prev_close = float(
            meta.get("chartPreviousClose")
            or meta.get("previousClose")
            or (closes[-24] if len(closes) >= 24 else (closes[0] if closes else last_price))
        )
        recent_highs = highs[-24:] if len(highs) >= 24 else highs
        recent_lows = lows[-24:] if len(lows) >= 24 else lows
        recent_vols = vols[-24:] if len(vols) >= 24 else vols

        high_24h = max([last_price, *(recent_highs or [last_price])])
        low_24h = min([last_price, *(recent_lows or [last_price])])
        # Apply realistic tight institutional spread (2 bps) around mid/last
        half_spread = max(last_price * 0.0001, 0.0001)
        bid = round(last_price - half_spread, 6)
        ask = round(last_price + half_spread, 6)
        change_pct = ((last_price - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0

        return {
            "pair": pair,
            "ask": ask,
            "bid": bid,
            "last": last_price,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "volume_24h": sum(recent_vols) if recent_vols else 0.0,
            "open": prev_close,
            "change_percent": change_pct,
            "source": "global_macro_feed",
        }

    async def _get_macro_ohlc(self, pair: str, yahoo_symbol: str, interval: int = 60) -> List[Dict]:
        yf_interval = "60m" if interval >= 60 else f"{max(5, interval)}m"
        chart = await self._yahoo_chart_request(yahoo_symbol, interval=yf_interval, range_str="1mo")
        timestamps = chart.get("timestamp") or []
        quote = ((chart.get("indicators") or {}).get("quote") or [{}])[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        parsed: List[Dict] = []
        for idx, ts in enumerate(timestamps):
            try:
                o = opens[idx] if idx < len(opens) else None
                h = highs[idx] if idx < len(highs) else None
                l = lows[idx] if idx < len(lows) else None
                c = closes[idx] if idx < len(closes) else None
                v = volumes[idx] if idx < len(volumes) else 0.0
                if o is None or h is None or l is None or c is None:
                    continue
                fo, fh, fl, fc = float(o), float(h), float(l), float(c)
                if min(fo, fh, fl, fc) <= 0:
                    continue
                parsed.append({
                    "timestamp": int(ts),
                    "open": fo,
                    "high": max(fo, fh, fl, fc),
                    "low": min(fo, fh, fl, fc),
                    "close": fc,
                    "vwap": round((fh + fl + fc) / 3.0, 6),
                    "volume": float(v or 0.0),
                })
            except (TypeError, ValueError):
                continue

        if not parsed:
            raise RuntimeError(f"No valid OHLC candles returned for {pair}.")
        return parsed

    async def get_ticker(self, pair: str) -> Dict:
        normalized_pair = pair.strip().upper()
        if normalized_pair in GLOBAL_MACRO_SYMBOL_MAP:
            return await self._get_macro_ticker(normalized_pair, GLOBAL_MACRO_SYMBOL_MAP[normalized_pair])

        result = await self._public_request("Ticker", {"pair": normalized_pair})
        if not result:
            raise RuntimeError("Kraken returned no ticker for the requested pair.")

        # Kraken's internal pair key can differ from its human-readable alias.
        raw = next(iter(result.values()))
        ticker = {
            "pair": normalized_pair,
            "ask": float((raw.get("a") or [0])[0]),
            "bid": float((raw.get("b") or [0])[0]),
            "last": float((raw.get("c") or [0])[0]),
            "high_24h": float((raw.get("h") or [0, 0])[1]),
            "low_24h": float((raw.get("l") or [0, 0])[1]),
            "volume_24h": float((raw.get("v") or [0, 0])[1]),
            "open": float(raw.get("o") or 0),
            "source": "kraken_spot_rest",
        }
        if ticker["last"] <= 0 or ticker["bid"] <= 0 or ticker["ask"] <= 0:
            raise RuntimeError("Kraken returned incomplete ticker data.")
        ticker["change_percent"] = (
            ((ticker["last"] - ticker["open"]) / ticker["open"]) * 100
            if ticker["open"] > 0 else 0.0
        )
        return ticker

    async def get_ohlc(self, pair: str, interval: int = 60) -> List[Dict]:
        normalized_pair = pair.strip().upper()
        if normalized_pair in GLOBAL_MACRO_SYMBOL_MAP:
            return await self._get_macro_ohlc(normalized_pair, GLOBAL_MACRO_SYMBOL_MAP[normalized_pair], interval=interval)

        result = await self._public_request(
            "OHLC",
            {"pair": normalized_pair, "interval": str(interval)},
        )
        candles = next((value for key, value in result.items() if key != "last"), None)
        if not isinstance(candles, list) or not candles:
            raise RuntimeError("Kraken returned no OHLC data for the requested pair.")

        parsed = []
        for candle in candles:
            if isinstance(candle, list) and len(candle) >= 7:
                parsed.append({
                    "timestamp": int(candle[0]),
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "vwap": float(candle[5]),
                    "volume": float(candle[6]),
                })
        if not parsed:
            raise RuntimeError("Kraken returned malformed OHLC data.")
        return parsed

    async def get_balance(self) -> Dict:
        balances = await self._private_request("Balance")
        normalized = {}
        for asset, amount in balances.items():
            try:
                value = float(amount)
            except (TypeError, ValueError):
                continue
            if value:
                normalized[asset] = value

        usd = normalized.pop("ZUSD", normalized.pop("USD", 0.0))
        return {
            "USD": usd,
            "holdings": normalized,
            "source": "kraken_private_balance",
        }

    async def execute_trade(self, symbol: str, side: str, volume: float) -> Dict:
        raise RuntimeError(
            "Order placement is disabled. A reviewed risk gate and execution lifecycle are required first."
        )
