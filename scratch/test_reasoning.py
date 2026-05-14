import os
import asyncio
from dotenv import load_dotenv
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from agents.reasoning import ReasoningAgent

async def test_reasoning():
    load_dotenv()
    
    print("--- Testing Reasoning Agent ---")
    print(f"GEMINI_API_KEY: {'Set' if os.getenv('GEMINI_API_KEY') else 'Not Set'}")
    print(f"FEATHERLESS_API_KEY: {'Set' if os.getenv('FEATHERLESS_API_KEY') else 'Not Set'}")
    
    agent = ReasoningAgent()
    
    transcript = """
    Alice: Hi everyone. We need to decide on the budget for the Q3 marketing campaign.
    Bob: I propose $50,000.
    Charlie: That sounds reasonable, but we need to ensure the ROI is above 200%.
    Alice: Agreed. Charlie, please prepare the detailed breakdown by next Tuesday.
    """
    
    print("\nSending transcript to agent...")
    try:
        result = await agent.analyze_multimodal(transcript)
        print("\n--- Agent Response ---")
        import json
        print(json.dumps(result, indent=2))
        
        if "Action Items" in result or "Action Items" in result:
            print("\n✅ Model is working and 'chatting' correctly!")
        else:
            print("\n⚠️ Model returned a response but format might be unexpected.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_reasoning())
