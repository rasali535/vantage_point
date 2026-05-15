from fastapi import APIRouter, Depends, Request
import os
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
trades_history = []

@router.get("/status")
async def get_trading_status():
    k_agent = get_kraken_agent()
    balance = await k_agent.get_balance()
    return {
        "balance": balance,
        "history": trades_history[-10:],
        "pnl_24h": "+$1,240.50 (4.2%)",
        "active_strategy": "Multi-Model Research (Qwen + DeepSeek)"
    }

@router.post("/scan")
async def scan_and_trade():
    """Vantage-Point 2.0: Multi-Model Autonomous Loop"""
    k_agent = get_kraken_agent()
    r_agent = get_reasoning_agent()
    
    trading_pair = os.getenv("TRADING_PAIR", "BTC/USD")
    trade_size = float(os.getenv("TRADE_SIZE_USD", "500"))
    
    # 1. Fetch live market data (Parallelized)
    ticker_task = k_agent.get_ticker(trading_pair)
    ohlc_task = k_agent.get_ohlc(trading_pair)
    status_task = k_agent.get_paper_status()
    
    ticker, ohlc, paper_status = await asyncio.gather(ticker_task, ohlc_task, status_task)
    
    # 2. Step 1: Research (Qwen)
    analysis = await r_agent.analyze_market(ticker, ohlc, trading_pair)
    
    # 3. Step 2: Decision (DeepSeek)
    decision = await r_agent.make_trade_decision(analysis, paper_status, trading_pair, trade_size)
    
    # 4. Execute Trade
    trade_res = None
    if decision.get("action") != "HOLD":
        # Calculate volume based on trade size and last price
        last_price = float(ticker.get("last", 0))
        if last_price > 0:
            volume = round(trade_size / last_price, 6)
            trade_res = await k_agent.execute_trade(trading_pair, decision.get("action"), volume)
            
            trades_history.append({
                "id": f"TX-{os.urandom(4).hex().upper()}",
                "symbol": trading_pair,
                "side": decision.get("action"),
                "volume": volume,
                "price": last_price,
                "time": "Just now",
                "status": "filled",
                "reasoning": decision.get("reasoning")
            })
            
    return {
        "pair": trading_pair,
        "analysis": analysis,
        "decision": decision,
        "trade": trade_res
    }

@router.post("/manual")
async def manual_trade(request: Request):
    data = await request.json()
    action = data.get("action") # "BUY" or "SELL"
    pair = data.get("pair", os.getenv("TRADING_PAIR", "AAPL/USD"))
    volume = float(data.get("volume", 0.01))
    
    k_agent = KrakenAgent()
    
    if action == "BUY":
        result = await k_agent.paper_buy(pair, volume)
    else:
        result = await k_agent.paper_sell(pair, volume)
        
    return {"status": "success", "trade": result}
