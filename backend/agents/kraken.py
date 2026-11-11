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

    async def get_ticker(self, pair: str) -> Dict:
        result = await self._public_request("Ticker", {"pair": pair})
        if not result:
            raise RuntimeError("Kraken returned no ticker for the requested pair.")

        # Kraken's internal pair key can differ from its human-readable alias.
        raw = next(iter(result.values()))
        ticker = {
            "pair": pair,
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
        result = await self._public_request(
            "OHLC",
            {"pair": pair, "interval": str(interval)},
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
