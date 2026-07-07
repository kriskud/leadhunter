"""Lead scoring — compute priority score from qualification signals."""

import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.database.models import Lead


def load_scoring_rules(path: Path | None = None) -> dict[str, int]:
    """Load scoring rules from JSON config."""
    rules_path = path or settings.scoring_rules_path
    with rules_path.open(encoding="utf-8") as f:
        return json.load(f)


async def score_lead(session: AsyncSession, lead: Lead) -> float:
    """
    Compute a priority score for a qualified lead.

    Args:
        session: Database session.
        lead: Lead with qualification data to score.

    Returns:
        Computed score value.

    Not implemented — extend using load_scoring_rules() and qualification signals.
    """
    raise NotImplementedError("Lead scoring is not implemented yet.")
