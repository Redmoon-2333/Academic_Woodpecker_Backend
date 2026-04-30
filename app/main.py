from contextlib import asynccontextmanager
import os
import uuid
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from pathlib import Path

from app.config import settings
from app.database import engine
from app.api.v1 import api_router
from app.core.logging import get_logger, TraceContext

logger = get_logger("main")

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        TraceContext.set_trace_id(trace_id)

        start_time = time.perf_counter()
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={"trace_id": trace_id},
        )

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"status={response.status_code} duration={duration_ms:.2f}ms",
                extra={"trace_id": trace_id},
            )
            response.headers["X-Trace-ID"] = trace_id
            return response
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"error={str(e)} duration={duration_ms:.2f}ms",
                extra={"trace_id": trace_id},
            )
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        from app.models.base import Base
        await conn.run_sync(Base.metadata.create_all)
    # Ensure uploads dir exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield
    await engine.dispose()


app = FastAPI(
    title="学业啄木鸟 - 智能学习分析平台",
    description="Academic Woodpecker - AI-powered learning analysis platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routers
app.include_router(api_router)

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "学业啄木鸟"}
