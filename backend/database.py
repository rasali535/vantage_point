"""MongoDB connection management for serverless FastAPI deployments.

PyMongo's native async client is reused by the ASGI process. If Atlas is
missing or unavailable, callers receive HTTP 503; the app never substitutes
synthetic balances, market data, or ledger entries.
"""
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import HTTPException
from pymongo import AsyncMongoClient

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "action_pilot")

_client: Optional[AsyncMongoClient] = None
_database = None


def _get_client() -> AsyncMongoClient:
    global _client

    if not MONGODB_URL:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured. Set MONGODB_URL in the server environment.",
        )

    if _client is None:
        # Vercel's horizontally scaled functions need small per-instance pools.
        # Start with five connections; tune only after observing Atlas metrics.
        _client = AsyncMongoClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            maxPoolSize=5,
            minPoolSize=0,
            maxIdleTimeMS=20000,
        )
    return _client


async def get_database():
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
        # Never log the MongoDB URI; it can contain database credentials.
        raise HTTPException(
            status_code=503,
            detail="MongoDB is temporarily unavailable. Stateful features are disabled.",
        ) from exc


async def close_database() -> None:
    """Close the cached async client during application shutdown."""
    global _client, _database
    if _client is not None:
        await _client.close()
    _client = None
    _database = None
