"""MongoDB connection management for serverless FastAPI deployments.

The client is created once per warm process and reused across invocations.
A missing or unavailable database is an application error: callers must not
silently substitute mock data or proceed with trading operations.
"""
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "action_pilot")

# Vercel functions are short-lived and can scale horizontally. Keep the pool
# conservative until real concurrency and Atlas connection metrics are known.
_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


def _get_client() -> AsyncIOMotorClient:
    global _client

    if not MONGODB_URL:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured. Set MONGODB_URL in the server environment.",
        )

    if _client is None:
        _client = AsyncIOMotorClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            maxPoolSize=5,
            minPoolSize=0,
            maxIdleTimeMS=20000,
        )
    return _client


async def get_database() -> AsyncIOMotorDatabase:
    """Return the configured database or fail closed with HTTP 503."""
    global _database

    if _database is not None:
        return _database

    client = _get_client()
    try:
        await client.admin.command("ping")
        _database = client[MONGODB_DB_NAME]
        return _database
    except Exception as exc:
        # Do not log the connection URI or credentials.
        raise HTTPException(
            status_code=503,
            detail="MongoDB is temporarily unavailable. Trading operations are disabled.",
        ) from exc


async def close_database() -> None:
    """Close the cached client during application shutdown."""
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None
