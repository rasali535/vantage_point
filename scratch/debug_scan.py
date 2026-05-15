import asyncio
import os
import json
import sys
from dotenv import load_dotenv

# Ensure we can import from backend
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from agents.kraken import KrakenAgent
from agents.reasoning import ReasoningAgent

load_dotenv()

async def debug_scan():
    print("--- STARTING SCAN DIAGNOSTIC ---")
    k_agent = KrakenAgent()
    r_agent = ReasoningAgent()
    
    pair = "BTC/USD"
    
    # 1. Data Fetch
    print(f"Step 1: Fetching data for {pair}...")
    try:
        ticker = await k_agent.get_ticker(pair)
        ohlc = await k_agent.get_ohlc(pair)
        status = await k_agent.get_paper_status()
        print(f"Data fetched. Ticker: {ticker.get('last')}")
    except Exception as e:
        print(f"Data fetch failed: {e}")
        return

    # 2. Research (Qwen)
    print("Step 2: Consulting Qwen for market research...")
    try:
        analysis = await r_agent.analyze_market(ticker, ohlc, pair)
        print(f"Research Complete. Analysis length: {len(analysis)}")
        print(f"Snippet: {analysis[:200]}")
    except Exception as e:
        print(f"Qwen Research failed: {e}")
        return

    # 3. Decision (DeepSeek)
    print("Step 3: Consulting DeepSeek for trade decision...")
    try:
        decision = await r_agent.make_trade_decision(analysis, status, pair, 500)
        print(f"Decision Complete: {json.dumps(decision, indent=2)}")
    except Exception as e:
        print(f"DeepSeek Decision failed: {e}")
        return

    # 4. Execution
    print("Step 4: Simulating execution...")
    try:
        if decision.get("action") != "HOLD":
            res = await k_agent.execute_trade(pair, decision.get("action"), 0.001)
            print(f"Execution Success: {res}")
        else:
            print("Decision was HOLD. Skipping execution.")
    except Exception as e:
        print(f"Execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_scan())
