from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.database.session import get_async_session

router = APIRouter()


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_async_session)) -> dict:
    """Health check endpoint — verifies API and database connectivity."""
    db_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "app": settings.app_name,
        "version": "0.1.0",
        "database": db_status,
    }
