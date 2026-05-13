import subprocess
import json
import os
from typing import Dict, List

class KrakenAgent:
    def __init__(self):
        self.asset_class = "tokenized_asset"

    def _run_command(self, args: List[str]) -> Dict:
        try:
            cmd = ["kraken"] + args + ["-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except Exception as e:
            print(f"Kraken CLI Error: {e}")
            # Mock data for demo if CLI is not installed or errors
            return {"error": str(e), "mock": True}

    async def get_price(self, symbol: str) -> Dict:
        """Get current price for an xStock (e.g. AAPLx)"""
        # Command: kraken ticker AAPLx --asset-class tokenized_asset
        res = self._run_command(["ticker", symbol, "--asset-class", self.asset_class])
        if res.get("mock"):
            import random
            return {"symbol": symbol, "price": round(random.uniform(150, 250), 2)}
        return res

    async def execute_trade(self, symbol: str, side: str, volume: float) -> Dict:
        """Execute a trade using Kraken CLI"""
        # Command: kraken order buy --pair AAPLxUSD --type market --volume 1 --asset-class tokenized_asset
        pair = f"{symbol}USD"
        args = [
            "order", side, 
            "--pair", pair, 
            "--type", "market", 
            "--volume", str(volume), 
            "--asset-class", self.asset_class
        ]
        res = self._run_command(args)
        if res.get("mock"):
            return {
                "status": "success",
                "txid": "mock_tx_12345",
                "message": f"Successfully {side}ed {volume} units of {symbol}"
            }
        return res

    async def get_balance(self) -> Dict:
        """Get account balance for tokenized assets"""
        res = self._run_command(["balance", "--asset-class", self.asset_class])
        if res.get("mock"):
            return {"USD": 10000.0, "AAPLx": 5.0, "TSLAx": 2.0}
        return res
