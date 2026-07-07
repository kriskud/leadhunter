"""Lead enrichment — scrape website data, extract contacts and signals."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import EnrichmentData, Lead


async def enrich_lead(session: AsyncSession, lead: Lead) -> EnrichmentData:
    """
    Enrich a lead by scraping its website and extracting structured data.

    Args:
        session: Database session.
        lead: Lead to enrich.

    Returns:
        Created EnrichmentData record.

    Not implemented — extend with Playwright page scraping.
    """
    raise NotImplementedError("Lead enrichment is not implemented yet.")
