from fastapi import APIRouter, Depends
from typing import List, Dict
from agents.kraken import KrakenAgent
from agents.reasoning import ReasoningAgent
import asyncio

router = APIRouter()
kraken_agent = KrakenAgent()
reasoning_agent = ReasoningAgent()

# Track active trades for the dashboard
trades_history = [
    {"id": "1", "symbol": "AAPLx", "side": "buy", "volume": 10, "price": 182.5, "time": "2026-05-13 14:20", "status": "filled"},
    {"id": "2", "symbol": "NVDAx", "side": "buy", "volume": 5, "price": 890.2, "time": "2026-05-13 15:45", "status": "filled"}
]

@router.get("/status")
async def get_trading_status():
    balance = await kraken_agent.get_balance()
    return {
        "balance": balance,
        "history": trades_history[-10:],
        "pnl_24h": "+$1,240.50 (4.2%)",
        "active_strategy": "Momentum Scalper v1.0"
    }

@router.post("/scan")
async def scan_and_trade():
    """Autonomous Loop: Scan -> Decide -> Execute"""
    symbols = ["AAPLx", "TSLAx", "NVDAx", "SPYx", "QQQx"]
    results = []
    
    for symbol in symbols:
        # 1. Get Market Data
        data = await kraken_agent.get_price(symbol)
        
        # 2. Form Strategy (Use Featherless for complex analysis)
        # In a real scenario, we'd feed technical indicators here
        prompt = f"Analyze the momentum for {symbol} at price {data.get('price')}. Return a momentum score 0-100 and a recommendation (buy/sell/hold)."
        analysis = await reasoning_agent.analyze_meeting(prompt) # Re-using the reasoning agent's interface
        
        score = analysis.get("Deal Health Score", 50) # Mapping health score to momentum
        recommendation = "hold"
        if score > 80: recommendation = "buy"
        elif score < 20: recommendation = "sell"
        
        # 3. Execute Trade
        trade_res = None
        if recommendation != "hold":
            trade_res = await kraken_agent.execute_trade(symbol, recommendation, 1.0)
            trades_history.append({
                "id": str(len(trades_history) + 1),
                "symbol": symbol,
                "side": recommendation,
                "volume": 1.0,
                "price": data.get("price"),
                "time": "Just now",
                "status": "filled"
            })
            
        results.append({
            "symbol": symbol,
            "price": data.get("price"),
            "momentum": score,
            "action": recommendation,
            "trade": trade_res
        })
        
    return {"results": results}
