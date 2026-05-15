import subprocess
import json
import os
import asyncio
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class KrakenAgent:
    def __init__(self):
        self.kraken_path = os.getenv("KRAKEN_CLI_PATH", "kraken")
        self.api_key = os.getenv("KRAKEN_API_KEY")
        self.api_secret = os.getenv("KRAKEN_API_SECRET")
        self.asset_class = "tokenized_asset"

    async def _run_cli(self, args: List[str]) -> str:
        """Executes Kraken CLI commands with a fallback for environments without the CLI (Vercel)."""
        try:
            cmd = [self.kraken_path] + args
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "KRAKEN_API_KEY": self.api_key, "KRAKEN_API_SECRET": self.api_secret}
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                print(f"CLI Error: {stderr.decode()}")
                return ""
            return stdout.decode().strip()
        except FileNotFoundError:
            print("⚠️ Kraken CLI not found. Falling back to Mock Engine.")
            return ""
        except Exception as e:
            print(f"Execution Error: {e}")
            return ""

    def _run(self, args: List[str]) -> Dict:
        try:
            env = os.environ.copy()
            if self.api_key: env["KRAKEN_API_KEY"] = self.api_key
            if self.api_secret: env["KRAKEN_API_SECRET"] = self.api_secret
            
            cmd = [self.kraken_path] + args + ["--output", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            if result.returncode != 0:
                # Silently return error for mock fallback
                return {"error": result.stderr.strip(), "mock": True}
            
            return json.loads(result.stdout)
        except Exception as e:
            return {"error": str(e), "mock": True}

    async def get_ticker(self, pair: str) -> Dict:
        res = self._run(["ticker", pair])
        if res.get("mock"):
            import random
            if "AAPL" in pair:
                price = round(random.uniform(170, 230), 2)
                vol = 1200000
            elif "BTC" in pair:
                price = round(random.uniform(60000, 90000), 2)
                vol = 1200
            else:
                price = round(random.uniform(100, 500), 2)
                vol = 5000
                
            return {
                "pair": pair, "ask": price + 0.05, "bid": price - 0.05, "last": price,
                "high_24h": price + 2.5, "low_24h": price - 2.5, "volume_24h": vol, "open": price - 1.2,
                "change_percent": round(random.uniform(-2, 2), 2)
            }
        
        raw = res.get(pair, {})
        return {
            "pair": pair,
            "ask": raw.get("a", [None])[0],
            "bid": raw.get("b", [None])[0],
            "last": raw.get("c", [None])[0],
            "high_24h": (raw.get("h") or [None, None])[1],
            "low_24h": (raw.get("l") or [None, None])[1],
            "volume_24h": (raw.get("v") or [None, None])[1],
            "open": raw.get("o"),
        }

    async def get_ohlc(self, pair: str, interval: int = 60) -> List[Dict]:
        res = self._run(["ohlc", pair, "--interval", str(interval)])
        if res.get("mock"):
            import time
            import random
            now = int(time.time())
            price_base = 180 if "AAPL" in pair else 75000
            return [
                {
                    "timestamp": now - (i * 3600), 
                    "open": price_base + random.uniform(-2, 2), 
                    "high": price_base + random.uniform(2, 5), 
                    "low": price_base - random.uniform(2, 5), 
                    "close": price_base + random.uniform(-1, 1), 
                    "volume": 1000 if "AAPL" in pair else 10
                } for i in range(12)
            ]
        
        candles = res.get(pair, []) if isinstance(res, dict) else res
        return [
            {
                "timestamp": c[0], "open": c[1], "high": c[2], "low": c[3],
                "close": c[4], "vwap": c[5], "volume": c[6]
            }
            for c in candles if isinstance(c, list) and len(c) >= 7
        ]

    async def get_paper_status(self) -> Dict:
        res = self._run(["paper", "status"])
        if res.get("mock"):
            return {"current_value": 10000.0, "holdings": {}, "currency": "USD"}
        return res

    async def execute_trade(self, symbol: str, side: str, volume: float) -> Dict:
        """Executes a paper trade for the demo"""
        # Mapping symbol for paper trading (BTC/USD)
        pair = symbol if "/" in symbol else f"{symbol}/USD"
        res = self._run(["paper", side.lower(), pair, str(volume), "--yes"])
        
        if res.get("mock"):
            return {
                "action": "market_order_filled",
                "mode": "paper",
                "order_id": f"PAPER-{os.urandom(4).hex().upper()}",
                "pair": pair,
                "side": side.lower(),
                "volume": volume,
                "status": "success"
            }
        return res

    async def get_balance(self) -> Dict:
        """Utility for dashboard display"""
        status = await self.get_paper_status()
        return {
            "USD": status.get("current_value", 0),
            "holdings": status.get("holdings", {})
        }
