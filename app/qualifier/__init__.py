"""Lead qualification — analyze enrichment data to assess fit."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Lead, Qualification


async def qualify_lead(session: AsyncSession, lead: Lead) -> Qualification:
    """
    Qualify a lead based on enrichment data and business rules.

    Args:
        session: Database session.
        lead: Lead with enrichment data to qualify.

    Returns:
        Created Qualification record.

    Not implemented — extend with rule-based or LLM-based qualification.
    """
    raise NotImplementedError("Lead qualification is not implemented yet.")
