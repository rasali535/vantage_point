from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
try:
    client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    db = client.action_pilot
    # Check connection
    # await client.admin.command('ping')
except Exception as e:
    print(f"MongoDB Error: {e}. Falling back to mock data mode.")
    db = None

async def get_database():
    return db
