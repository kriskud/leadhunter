"""Lead collection from external sources (maps, directories, etc.)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.collector.google_maps import collect_google_maps
from app.database.models import Lead

__all__ = ["collect_leads", "collect_google_maps"]


async def collect_leads(
    session: AsyncSession,
    *,
    city: str,
    category: str,
    limit: int = 50,
) -> list[Lead]:
    """
    Collect raw leads from Google Maps and persist via the provided session.

    Args:
        session: Database session for persisting leads.
        city: Target city for search.
        category: Business category to search for.
        limit: Maximum number of places to scrape.

    Returns:
        List of newly created Lead records.
    """
    return await collect_google_maps(category, city, limit, session=session)
