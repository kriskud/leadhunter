"""Lead scoring — compute priority score from qualification signals."""

from functools import lru_cache
import json
import re
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.database.base import LeadStatus
from app.database.models import Lead


@lru_cache(maxsize=1)
def load_scoring_rules(path: Path | None = None) -> dict:
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
    """
    # Ensure qualification and enrichment are loaded to avoid lazy-loading issues in async session
    try:
        await session.refresh(lead, ["qualification", "enrichment"])
    except Exception:
        pass

    rules = load_scoring_rules()
    score = 0.0

    # 1. Base contact presence & Mutual exclusion of website and social links
    has_main_website = False
    is_social_website = False
    social_domains = ["instagram.com", "t.me", "vk.com", "taplink.cc"]

    if lead.website and lead.website.strip():
        web_lower = lead.website.lower()
        if any(sd in web_lower for sd in social_domains):
            is_social_website = True
        else:
            has_main_website = True

    # Check if lead has any contacts (phone, or enrichment contact fields, or if website is a social link)
    has_any_contacts = False
    if lead.phone and lead.phone.strip():
        has_any_contacts = True
    if is_social_website:
        has_any_contacts = True
    if lead.enrichment:
        if lead.enrichment.emails and lead.enrichment.emails.strip():
            has_any_contacts = True
        if lead.enrichment.phones and lead.enrichment.phones.strip():
            has_any_contacts = True
        if lead.enrichment.social_links and lead.enrichment.social_links.strip():
            has_any_contacts = True
        if lead.enrichment.booking_links and lead.enrichment.booking_links.strip():
            has_any_contacts = True

    if has_main_website:
        score += rules.get("has_website", 0)
    elif has_any_contacts:
        score += rules.get("only_social_links", 0)

    # 1b. Base phone score
    if lead.phone and lead.phone.strip():
        score += rules.get("has_phone", 0)

    # 2. Qualification signals
    qual = lead.qualification
    if qual:
        if qual.is_private_practice:
            score += rules.get("private_practice", 0)
        
        if qual.has_online_booking is False:
            score += rules.get("no_online_booking", 0)
        
        if qual.booking_provider:
            provider_lower = qual.booking_provider.lower()
            if "telegram" in provider_lower:
                score += rules.get("telegram_booking", 0)
            if "altegio" in provider_lower:
                score += rules.get("has_altegio", 0)

        if qual.estimated_staff_count is not None and qual.estimated_staff_count > 5:
            score += rules.get("staff_over_5", 0)

    # 3. Micro-business signals from contacts/enrichment (has_whatsapp / has_telegram)
    has_wa = False
    has_tg = False

    # Collect all contact/phone/link fields
    contact_strings = []
    if lead.phone:
        contact_strings.append(lead.phone)
    if lead.website:
        contact_strings.append(lead.website)
    if lead.enrichment:
        if lead.enrichment.phones:
            contact_strings.append(lead.enrichment.phones)
        if lead.enrichment.emails:
            contact_strings.append(lead.enrichment.emails)
        if lead.enrichment.social_links:
            contact_strings.append(lead.enrichment.social_links)
        if lead.enrichment.booking_links:
            contact_strings.append(lead.enrichment.booking_links)

    for s in contact_strings:
        s_lower = s.lower()
        if "wa.me" in s_lower or "whatsapp" in s_lower:
            has_wa = True
        if "t.me" in s_lower or "telegram" in s_lower:
            has_tg = True

    if has_wa:
        score += rules.get("has_whatsapp", 0)
    if has_tg:
        score += rules.get("has_telegram", 0)

    # 3b. gmail_email
    has_gmail = False
    if lead.enrichment and lead.enrichment.emails:
        # Split by whitespace, commas, semicolons to find individual emails
        email_candidates = re.split(r"[\s,;]+", lead.enrichment.emails)
        for email in email_candidates:
            email_clean = email.strip().lower()
            if email_clean.endswith("@gmail.com"):
                has_gmail = True
                break

    if has_gmail:
        score += rules.get("gmail_email", 0)

    # 4. Category bonuses and penalties (iterative checking)
    if lead.category:
        cat_lower = lead.category.lower()
        
        category_bonuses = rules.get("category_bonuses", {})
        for kw, value in category_bonuses.items():
            if kw.lower() in cat_lower:
                score += value

        category_penalties = rules.get("category_penalties", {})
        for kw, value in category_penalties.items():
            if kw.lower() in cat_lower:
                score += value

    # 4b. Name bonuses and penalties — business name carries the strongest
    # private-vs-organization signal (category holds the search query only)
    if lead.name:
        name_lower = lead.name.lower()

        for kw, value in rules.get("name_bonuses", {}).items():
            if kw.lower() in name_lower:
                score += value

        for kw, value in rules.get("name_penalties", {}).items():
            if kw.lower() in name_lower:
                score += value

    # Update Lead object
    lead.score = float(score)
    threshold = rules.get("min_score_threshold", 20)
    if score >= threshold:
        lead.status = LeadStatus.SCORED
    else:
        lead.status = LeadStatus.REJECTED

    return float(score)
