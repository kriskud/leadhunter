"""Message builder — generate outreach messages for qualified leads."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Lead, MessageDraft


async def generate_message(session: AsyncSession, lead: Lead) -> MessageDraft:
    """
    Generate a personalized outreach message for a scored lead.

    Args:
        session: Database session.
        lead: Lead with qualification and score data.

    Returns:
        Created MessageDraft record.

    Not implemented — extend with template-based or LLM-based generation.
    """
    raise NotImplementedError("Message generation is not implemented yet.")
