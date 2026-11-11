from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import routes.meetings
import routes.trading
import routes.chat
from database import close_database, get_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_database()


app = FastAPI(title="Ras Ali AI Trader API", version="0.2.0", lifespan=lifespan)

# Explicit origins only. Add production and preview frontend origins through
# CORS_ORIGINS (comma-separated) in the deployment environment.
_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://actionpilot.vercel.app",
]
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", ",".join(_default_origins)).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(routes.meetings.router, prefix="/api/meetings", tags=["Meetings"])
app.include_router(routes.trading.router, prefix="/api/trading", tags=["Trading"])
app.include_router(routes.chat.router, prefix="/api/chat", tags=["Chat"])


@app.get("/")
async def root():
    return {"message": "Ras Ali AI Trader API", "status": "online"}


@app.get("/health")
async def health():
    # Readiness is explicit: a process without MongoDB is not ready to serve
    # stateful trading features.
    await get_database()
    return {"status": "ready", "database": "connected"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
