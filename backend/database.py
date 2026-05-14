from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
db = None

# We don't try to connect here because we want to be able to start the app 
# even if the DB is down. The actual connection check happens in get_database.
client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=2000)

async def get_database():
    global db
    if db is not None:
        return db
        
    try:
        # Check if we can actually reach the server
        await client.admin.command('ping')
        print("✅ MongoDB Connected Successfully")
        db = client.action_pilot
        return db
    except Exception as e:
        # Silently fail and return None to trigger mock data in routes
        return None
