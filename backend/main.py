from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

import routes.meetings
import routes.trading
import routes.chat
from database import close_database, ping_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_database()


app = FastAPI(title="Ras Ali AI Trader API", version="0.2.0", lifespan=lifespan)


@app.exception_handler(PyMongoError)
async def mongodb_unavailable_handler(request, exc):
    # A cached client can lose its Atlas connection after startup. Normalize
    # subsequent driver failures to 503 instead of leaking internal errors.
    return JSONResponse(
        status_code=503,
        content={"detail": "MongoDB is temporarily unavailable. No trading action was executed."},
    )

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
    allow_headers=["Authorization", "Content-Type", "X-Paper-Token"],
)

app.include_router(routes.meetings.router, prefix="/api/meetings", tags=["Meetings"])
app.include_router(routes.trading.router, prefix="/api/trading", tags=["Trading"])
app.include_router(routes.chat.router, prefix="/api/chat", tags=["Chat"])


@app.get("/")
async def root():
    return {"message": "Ras Ali AI Trader API", "status": "online"}


@app.get("/health")
@app.get("/api/health")
async def health():
    # Ping on each health request so Atlas restarts are visible immediately.
    await ping_database()
    return {"status": "ready", "database": "connected"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
