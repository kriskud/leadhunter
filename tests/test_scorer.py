import pytest
from unittest.mock import AsyncMock, MagicMock

from app.database.base import LeadStatus
from app.database.models import Lead, Qualification, EnrichmentData
from app.scorer import load_scoring_rules, score_lead


def test_load_scoring_rules():
    rules = load_scoring_rules()
    assert isinstance(rules, dict)
    assert rules["min_score_threshold"] == 20
    assert rules["has_website"] == 8
    assert rules["category_bonuses"]["перманент"] == 15


@pytest.mark.asyncio
async def test_score_lead_rejected():
    session = AsyncMock()
    
    # Lead that doesn't meet the threshold
    lead = Lead(
        name="Test Lead Low",
        website="http://example.com",
        phone="12345678",
        category="b2b опт",
        status=LeadStatus.NEW,
    )
    # Ensure no qualification and enrichment
    lead.qualification = None
    lead.enrichment = None

    score = await score_lead(session, lead)
    
    # has_website (8) + has_phone (1) + b2b penalty (-20) + опт penalty (-20) = -31
    assert score == -31.0
    assert lead.score == -31.0
    assert lead.status == LeadStatus.REJECTED


@pytest.mark.asyncio
async def test_score_lead_scored():
    session = AsyncMock()
    
    # Premium private practice lead
    lead = Lead(
        name="Premium Artist",
        website="http://instagram.com/artist",
        phone="whatsapp: +79998887766",
        category="перманентный макияж",
        status=LeadStatus.NEW,
    )
    
    lead.qualification = Qualification(
        is_private_practice=True,
        has_online_booking=False,
        booking_provider="telegram bot",
        estimated_staff_count=1,
    )
    
    lead.enrichment = EnrichmentData(
        social_links="https://instagram.com/artist https://t.me/artist_channel",
        booking_links="https://wa.me/79998887766",
        emails="artist@gmail.com",
        page_text="Beautiful permanent tattoos and makeup",
    )

    score = await score_lead(session, lead)
    
    # only_social_links (10)
    # has_phone (1)
    # is_private_practice (15)
    # has_online_booking is False (3)
    # telegram_booking (10)
    # has_whatsapp from phone/enrichment (5)
    # has_telegram from enrichment (5)
    # gmail_email (1)
    # category_bonuses "перманент" (15)
    # Total score should be 10 + 1 + 15 + 3 + 10 + 5 + 5 + 1 + 15 = 65
    assert score == 65.0
    assert lead.score == 65.0
    assert lead.status == LeadStatus.SCORED
