from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collector import collect_google_maps, collect_leads
from app.database.base import LeadStatus
from app.database.models import Lead
from app.database.session import get_async_session

router = APIRouter()


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    website: str | None
    phone: str | None
    category: str | None
    city: str | None
    source: str | None
    status: LeadStatus
    score: float | None
    created_at: datetime
    updated_at: datetime


class CollectRequest(BaseModel):
    category: str = Field(..., min_length=1, examples=["психолог"])
    city: str = Field(..., min_length=1, examples=["Санкт-Петербург"])
    limit: int = Field(default=50, ge=1, le=200)


class CollectResponse(BaseModel):
    message: str
    leads: list[LeadResponse]


@router.get("", response_model=list[LeadResponse])
async def list_leads(
    session: AsyncSession = Depends(get_async_session),
    skip: int = 0,
    limit: int = 50,
) -> list[Lead]:
    """List leads with pagination."""
    result = await session.execute(
        select(Lead).order_by(Lead.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


@router.post("/collect", response_model=CollectResponse)
async def collect_from_google_maps(
    body: CollectRequest,
    session: AsyncSession = Depends(get_async_session),
) -> CollectResponse:
    """Collect leads from Google Maps synchronously (may take several minutes)."""
    leads = await collect_leads(
        session,
        category=body.category,
        city=body.city,
        limit=body.limit,
    )
    return CollectResponse(
        message=f"Collected {len(leads)} new leads from Google Maps",
        leads=leads,
    )


@router.post("/collect/async", status_code=202)
async def collect_from_google_maps_async(
    body: CollectRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Start Google Maps collection in the background."""

    async def _run() -> None:
        await collect_google_maps(body.category, body.city, body.limit)

    background_tasks.add_task(_run)
    return {
        "message": "Collection started in background",
        "category": body.category,
        "city": body.city,
    }


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> Lead:
    """Get a single lead by ID."""
    result = await session.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
