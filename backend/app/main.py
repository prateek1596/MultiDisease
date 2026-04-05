"""
Multi-Disease Prediction System — FastAPI Backend v3.0
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from loguru import logger

from app.core.config import settings
from app.core.database import init_db
from app.routes import predict, models, report, auth, train, fairness, minimal_features
from app.routes.advanced import router as advanced_router
from app.utils.logger import setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()
    logger.info(f"Starting {settings.APP_NAME} v3.0")
    await init_db()
    for d in [settings.MODEL_SAVE_PATH, settings.REPORT_SAVE_PATH, settings.DATA_PATH]:
        os.makedirs(d, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    logger.info("Startup complete")
    yield
    logger.info("Shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-Disease Prediction System — Heart, Diabetes, Kidney",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("reports", exist_ok=True)
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth.router,             prefix="/api/auth",  tags=["Authentication"])
app.include_router(predict.router,          prefix="/api",       tags=["Prediction"])
app.include_router(models.router,           prefix="/api",       tags=["Models"])
app.include_router(report.router,           prefix="/api",       tags=["Reports"])
app.include_router(train.router,            prefix="/api",       tags=["Training"])
app.include_router(fairness.router,         prefix="/api",       tags=["Fairness"])
app.include_router(minimal_features.router, prefix="/api",       tags=["Minimal Features"])
app.include_router(advanced_router,         prefix="/api",       tags=["Advanced"])


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": settings.APP_NAME, "version": "3.0.0"}

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "env": settings.APP_ENV}
