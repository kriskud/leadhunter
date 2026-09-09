"""2GIS lead collector — official Places API (catalog.api.2gis.com).

Требует DGIS_API_KEY в .env (ключ Places API с dev.2gis.com).
В отличие от Google Maps, сети отсекаются по числу филиалов (org.branch_count)
ещё до сохранения.
"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collector.filters import excluded_by_stopword
from app.config.settings import settings
from app.database.base import LeadStatus
from app.database.models import Lead
from app.database.session import async_session_factory

logger = logging.getLogger(__name__)

SOURCE = "2gis"
API_BASE = "https://catalog.api.2gis.com"
PAGE_SIZE = 50
ITEM_FIELDS = "items.contact_groups,items.org,items.address,items.rubrics"


class DgisError(RuntimeError):
    pass


def _require_key() -> str:
    key = settings.dgis_api_key
    if not key:
        raise DgisError(
            "DGIS_API_KEY не задан в .env — получите ключ Places API на https://dev.2gis.com"
        )
    return key


async def _api_get(client: httpx.AsyncClient, path: str, params: dict) -> dict:
    response = await client.get(f"{API_BASE}{path}", params={**params, "key": _require_key()})
    payload = response.json()
    meta = payload.get("meta", {})
    if meta.get("code") != 200:
        error = meta.get("error", {})
        raise DgisError(f"2GIS API error {meta.get('code')}: {error.get('message', payload)}")
    return payload.get("result", {})


async def _region_id(client: httpx.AsyncClient, city: str) -> str:
    result = await _api_get(client, "/2.0/region/search", {"q": city})
    items = result.get("items", [])
    if not items:
        raise DgisError(f"2GIS не нашёл регион для города {city!r}")
    region = items[0]
    logger.info("Region for %r: id=%s name=%r", city, region["id"], region.get("name"))
    return str(region["id"])


def _extract_contacts(item: dict) -> tuple[str | None, str | None]:
    """Return (phone, website) from contact_groups."""
    phone = None
    website = None
    for group in item.get("contact_groups") or []:
        for contact in group.get("contacts") or []:
            ctype = contact.get("type")
            if ctype == "phone" and not phone:
                phone = contact.get("value")
            elif ctype == "website" and not website:
                website = contact.get("url") or contact.get("value")
    return phone, website


def _branch_count(item: dict) -> int:
    org = item.get("org") or {}
    return int(org.get("branch_count") or 1)


async def _fetch_items(category: str, region_id: str, limit: int, client: httpx.AsyncClient) -> list[dict]:
    items: list[dict] = []
    page = 1
    while len(items) < limit:
        params = {
            "q": category,
            "region_id": region_id,
            "type": "branch",
            "page": page,
            "page_size": min(PAGE_SIZE, limit - len(items)),
            "locale": "ru_RU",
            "fields": ITEM_FIELDS,
        }
        try:
            result = await _api_get(client, "/3.0/items", params)
        except DgisError as exc:
            # 2GIS отдаёт 404 в meta, когда страницы закончились
            if "404" in str(exc):
                break
            raise
        batch = result.get("items", [])
        if not batch:
            break
        items.extend(batch)
        total = int(result.get("total", 0))
        logger.info("Fetched page %d: %d items (total available: %d)", page, len(batch), total)
        if page * PAGE_SIZE >= total:
            break
        page += 1
    return items[:limit]


async def collect_dgis(
    category: str,
    city: str,
    limit: int = 100,
    *,
    session: AsyncSession | None = None,
    max_branches: int = 2,
) -> list[Lead]:
    """Collect leads from 2GIS Places API and persist them."""
    async with httpx.AsyncClient(timeout=30) as client:
        region_id = await _region_id(client, city)
        items = await _fetch_items(category, region_id, limit, client)

    logger.info("2GIS returned %d items for %r in %r", len(items), category, city)

    if session is not None:
        return await _persist(session, items, category=category, city=city, max_branches=max_branches)

    async with async_session_factory() as own_session:
        leads = await _persist(own_session, items, category=category, city=city, max_branches=max_branches)
        await own_session.commit()
        return leads


async def _persist(
    session: AsyncSession,
    items: list[dict],
    *,
    category: str,
    city: str,
    max_branches: int,
) -> list[Lead]:
    # Дедуп по (имя, телефон) поверх всех источников — один и тот же косметолог
    # мог прийти и из Google Maps.
    existing = await session.execute(select(Lead.name, Lead.phone).where(Lead.city == city))
    existing_keys = {(name.strip().lower(), phone) for name, phone in existing.all()}

    saved: list[Lead] = []
    skipped_stopword = skipped_branches = skipped_dupes = 0

    for item in items:
        name = (item.get("name") or "").strip()
        if not name:
            continue

        stopword = excluded_by_stopword(name)
        if stopword:
            skipped_stopword += 1
            logger.info("Skipping %r — stopword %r", name, stopword)
            continue

        branches = _branch_count(item)
        if branches > max_branches:
            skipped_branches += 1
            logger.info("Skipping %r — %d branches (network)", name, branches)
            continue

        phone, website = _extract_contacts(item)
        key = (name.lower(), phone)
        if key in existing_keys:
            skipped_dupes += 1
            continue

        lead = Lead(
            name=name,
            website=website,
            phone=phone,
            category=category,
            city=city,
            source=SOURCE,
            status=LeadStatus.NEW,
        )
        session.add(lead)
        saved.append(lead)
        existing_keys.add(key)

    await session.flush()
    logger.info(
        "Persisted %d leads (skipped: %d stopwords, %d networks, %d duplicates)",
        len(saved), skipped_stopword, skipped_branches, skipped_dupes,
    )
    return saved
