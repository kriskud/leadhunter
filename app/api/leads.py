from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
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


class LeadListResponse(BaseModel):
    total: int
    items: list[LeadResponse]


class FacetsResponse(BaseModel):
    cities: list[str]
    categories: list[str]
    statuses: list[str]


class CollectRequest(BaseModel):
    category: str = Field(..., min_length=1, examples=["психолог"])
    city: str = Field(..., min_length=1, examples=["Санкт-Петербург"])
    limit: int = Field(default=50, ge=1, le=200)


class CollectResponse(BaseModel):
    message: str
    leads: list[LeadResponse]


@router.get("", response_model=LeadListResponse)
async def list_leads(
    session: AsyncSession = Depends(get_async_session),
    skip: int = 0,
    limit: int = Query(default=50, ge=1, le=500),
    city: str | None = None,
    category: str | None = None,
    status: LeadStatus | None = None,
    min_score: float | None = None,
    q: str | None = Query(default=None, description="Substring search in lead name"),
    sort: Literal["score", "created_at"] = "score",
) -> LeadListResponse:
    """List leads with filtering, sorting and pagination."""
    query = select(Lead)
    if city:
        query = query.where(Lead.city == city)
    if category:
        query = query.where(Lead.category == category)
    if status:
        query = query.where(Lead.status == status)
    if min_score is not None:
        query = query.where(Lead.score >= min_score)
    if q:
        query = query.where(Lead.name.ilike(f"%{q}%"))

    total = await session.scalar(select(func.count()).select_from(query.subquery()))

    if sort == "score":
        query = query.order_by(Lead.score.desc().nulls_last(), Lead.created_at.desc())
    else:
        query = query.order_by(Lead.created_at.desc())

    result = await session.execute(query.offset(skip).limit(limit))
    leads = list(result.scalars().all())
    return LeadListResponse(total=total or 0, items=leads)


@router.get("/facets", response_model=FacetsResponse)
async def list_facets(
    session: AsyncSession = Depends(get_async_session),
) -> FacetsResponse:
    """Distinct filter values for the UI dropdowns."""
    cities = await session.scalars(
        select(Lead.city).where(Lead.city.is_not(None)).distinct().order_by(Lead.city)
    )
    categories = await session.scalars(
        select(Lead.category)
        .where(Lead.category.is_not(None))
        .distinct()
        .order_by(Lead.category)
    )
    return FacetsResponse(
        cities=list(cities),
        categories=list(categories),
        statuses=[s.value for s in LeadStatus],
    )


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
