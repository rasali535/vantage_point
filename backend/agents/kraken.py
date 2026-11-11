import asyncio
import json
import os
import subprocess
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()


class KrakenAgent:
    """Server-side Kraken CLI adapter.

    This adapter deliberately fails closed. It never invents prices, balances,
    candle data, order IDs, or fills when the CLI/exchange is unavailable.
    """

    def __init__(self):
        self.kraken_path = os.getenv("KRAKEN_CLI_PATH", "kraken")
        self.api_key = os.getenv("KRAKEN_API_KEY")
        self.api_secret = os.getenv("KRAKEN_API_SECRET")

    async def _run(self, args: List[str]) -> Dict:
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Kraken credentials are not configured on the server.")

        env = os.environ.copy()
        env["KRAKEN_API_KEY"] = self.api_key
        env["KRAKEN_API_SECRET"] = self.api_secret

        command_args = list(args)
        if "-o" not in command_args and "--output" not in command_args:
            command_args.extend(["-o", "json"])

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [self.kraken_path, *command_args],
                capture_output=True,
                text=True,
                env=env,
                timeout=8.0,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("Kraken CLI is unavailable or timed out.") from exc

        if result.returncode != 0:
            # CLI stderr can contain sensitive diagnostics; do not expose it.
            raise RuntimeError("Kraken request failed.")

        try:
            payload = json.loads(result.stdout)
        except (TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Kraken returned an invalid response.") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("Kraken returned an unexpected response.")
        if payload.get("error"):
            raise RuntimeError("Kraken reported an exchange error.")
        return payload

    async def get_ticker(self, pair: str) -> Dict:
        args = ["ticker", pair]
        if "x/" in pair:
            args.extend(["--asset-class", "tokenized_asset"])

        response = await self._run(args)
        raw = response.get(pair)
        if not isinstance(raw, dict) and response:
            raw = next(iter(response.values()))
        if not isinstance(raw, dict):
            raise RuntimeError("Kraken did not return ticker data for the requested pair.")

        ticker = {
            "pair": pair,
            "ask": float((raw.get("a") or [0])[0]),
            "bid": float((raw.get("b") or [0])[0]),
            "last": float((raw.get("c") or [0])[0]),
            "high_24h": float((raw.get("h") or [0, 0])[1]),
            "low_24h": float((raw.get("l") or [0, 0])[1]),
            "volume_24h": float((raw.get("v") or [0, 0])[1]),
            "open": float(raw.get("o") or 0),
            "source": "kraken",
        }
        if ticker["last"] <= 0 or ticker["bid"] <= 0 or ticker["ask"] <= 0:
            raise RuntimeError("Kraken returned incomplete ticker data.")
        ticker["change_percent"] = (
            ((ticker["last"] - ticker["open"]) / ticker["open"]) * 100
            if ticker["open"] > 0 else 0.0
        )
        return ticker

    async def get_ohlc(self, pair: str, interval: int = 60) -> List[Dict]:
        response = await self._run(["ohlc", pair, "--interval", str(interval)])
        candles = response.get(pair, [])
        if not isinstance(candles, list) or not candles:
            raise RuntimeError("Kraken did not return OHLC data for the requested pair.")

        parsed = []
        for candle in candles:
            if isinstance(candle, list) and len(candle) >= 7:
                parsed.append({
                    "timestamp": candle[0],
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

    async def get_paper_status(self) -> Dict:
        response = await self._run(["paper", "status"])
        if "current_value" not in response:
            raise RuntimeError("Kraken paper account status is unavailable.")
        return response

    async def execute_trade(self, symbol: str, side: str, volume: float) -> Dict:
        if side.lower() not in {"buy", "sell"}:
            raise ValueError("Trade side must be buy or sell.")
        if volume <= 0:
            raise ValueError("Trade volume must be greater than zero.")

        pair = symbol if "/" in symbol else f"{symbol}/USD"
        return await self._run(["paper", side.lower(), pair, str(volume), "--yes"])

    async def get_balance(self) -> Dict:
        status = await self.get_paper_status()
        return {
            "USD": status.get("current_value", 0),
            "holdings": status.get("holdings", {}),
            "source": "kraken_paper",
        }
