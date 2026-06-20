from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.core.runtime_store import RuntimeStore
from app.db.database import SessionLocal


router = APIRouter(tags=["health"])


@router.get("/")
def root():
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
def health_check():
    settings = get_settings()
    db_status = "ok"
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception:
        db_status = "error"

    runtime_store = RuntimeStore()
    redis_status = "ok" if runtime_store._client is not None else "degraded"

    data_paths = {
        "data_dir": settings.data_dir,
        "uploads_dir": settings.uploads_dir,
        "reports_dir": settings.reports_dir,
    }

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": settings.app_name,
        "version": settings.app_version,
        "provider": settings.llm_provider,
        "sam_profile": settings.sam_profile,
        "checks": {
            "database": db_status,
            "runtime_store": redis_status,
            "storage": {name: Path(path).exists() for name, path in data_paths.items()},
        },
    }
