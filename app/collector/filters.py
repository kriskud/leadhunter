"""Shared collection-stage filters for all collectors."""

import logging

from app.scorer import load_scoring_rules

logger = logging.getLogger(__name__)


def excluded_by_stopword(name: str) -> str | None:
    """Return the matched stopword if the business name marks a non-target org."""
    name_lower = name.lower()
    for word in load_scoring_rules().get("collect_name_stopwords", []):
        if word.lower() in name_lower:
            return word
    return None
