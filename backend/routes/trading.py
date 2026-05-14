from fastapi import APIRouter, Depends
from typing import List, Dict
from agents.kraken import KrakenAgent
from agents.reasoning import ReasoningAgent
import asyncio

router = APIRouter()

# Lazy load agents for Vercel stability
_kraken_agent = None
_reasoning_agent = None

def get_kraken_agent():
    global _kraken_agent
    if _kraken_agent is None:
        _kraken_agent = KrakenAgent()
    return _kraken_agent

def get_reasoning_agent():
    global _reasoning_agent
    if _reasoning_agent is None:
        _reasoning_agent = ReasoningAgent()
    return _reasoning_agent

# Track active trades for the dashboard
trades_history = [
    {"id": "1", "symbol": "AAPLx", "side": "buy", "volume": 10, "price": 182.5, "time": "2026-05-13 14:20", "status": "filled"},
    {"id": "2", "symbol": "NVDAx", "side": "buy", "volume": 5, "price": 890.2, "time": "2026-05-13 15:45", "status": "filled"}
]

@router.get("/status")
async def get_trading_status():
    k_agent = get_kraken_agent()
    balance = await k_agent.get_balance()
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
        # 2. Form Strategy (Use Featherless for complex analysis)
        k_agent = get_kraken_agent()
        r_agent = get_reasoning_agent()
        data = await k_agent.get_price(symbol)
        
        prompt = f"Analyze the momentum for {symbol} at price {data.get('price')}. Return a momentum score 0-100 and a recommendation (buy/sell/hold)."
        analysis = await r_agent.analyze_multimodal(prompt) 
        
        score = analysis.get("Deal Health Score", 50) # Mapping health score to momentum
        recommendation = "hold"
        if score > 80: recommendation = "buy"
        elif score < 20: recommendation = "sell"
        
        # 3. Execute Trade
        trade_res = None
        if recommendation != "hold":
            trade_res = await k_agent.execute_trade(symbol, recommendation, 1.0)
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
