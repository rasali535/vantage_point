from contextlib import asynccontextmanager
import logging
import os
import traceback
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

import routes.meetings
import routes.trading
import routes.chat
from database import close_database, ping_database
from paper_trading.autopilot import start_worker, stop_worker


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_worker()
    try:
        yield
    finally:
        await stop_worker()
        await close_database()


app = FastAPI(title="Ras Ali AI Trader API", version="0.2.0", lifespan=lifespan)


@app.exception_handler(PyMongoError)
async def mongodb_unavailable_handler(request, exc):
    # Preserve the safe public response while exposing enough server-side
    # context to identify the failing MongoDB operation. Do not log exception
    # messages because driver errors can contain connection details.
    request_id = uuid.uuid4().hex
    frames = traceback.extract_tb(exc.__traceback__)
    locations = " <- ".join(
        f"{frame.filename}:{frame.lineno}:{frame.name}" for frame in frames[-6:]
    )
    logger.error(
        "mongodb_operation_failed request_id=%s method=%s path=%s error_type=%s "
        "code=%s code_name=%s traceback=%s",
        request_id,
        request.method,
        request.url.path,
        type(exc).__name__,
        getattr(exc, "code", None),
        getattr(exc, "code_name", None),
        locations,
    )
    return JSONResponse(
        status_code=503,
        content={
            "detail": "MongoDB is temporarily unavailable. No trading action was executed.",
            "request_id": request_id,
        },
    )


# Explicit origins only. Keep the production Hostinger frontend in the
# built-in allowlist so a missing or incomplete Vercel CORS_ORIGINS value
# cannot silently break the deployed dashboard. Additional trusted origins
# can be supplied as a comma-separated CORS_ORIGINS environment variable.
_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://actionpilot.vercel.app",
    "https://darkblue-turkey-867661.hostingersite.com",
]
_configured_origins = os.getenv("CORS_ORIGINS", "").split(",")
allowed_origins = list(dict.fromkeys(
    origin.strip().rstrip("/")
    for origin in [*_default_origins, *_configured_origins]
    if origin.strip()
))
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
