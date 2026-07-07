"""REST API routes."""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.leads import router as leads_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(leads_router, prefix="/leads", tags=["leads"])
