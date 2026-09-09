import asyncio
from unittest.mock import AsyncMock

from app.database.base import LeadStatus
from app.database.models import Lead, Qualification, EnrichmentData
from app.scorer import load_scoring_rules, score_lead


def test_load_scoring_rules():
    print("Testing load_scoring_rules...")
    rules = load_scoring_rules()
    assert isinstance(rules, dict)
    assert rules["min_score_threshold"] == 20
    assert rules["has_website"] == 8
    assert rules["category_bonuses"]["косметолог"] == 15
    assert rules["name_penalties"]["клиник"] == -25
    print("load_scoring_rules test passed successfully!")


async def test_score_lead_rejected():
    print("Testing score_lead (rejected)...")
    session = AsyncMock()
    
    # Lead that doesn't meet the threshold
    lead = Lead(
        name="Test Lead Low",
        website="http://example.com",
        phone="12345678",
        category="b2b опт",
        status=LeadStatus.NEW,
    )
    lead.qualification = None
    lead.enrichment = None

    score = await score_lead(session, lead)
    
    # has_website (8) + has_phone (1) + b2b penalty (-20) + опт penalty (-20) = -31
    assert score == -31.0
    assert lead.score == -31.0
    assert lead.status == LeadStatus.REJECTED
    print("score_lead (rejected) test passed successfully!")


async def test_score_lead_scored():
    print("Testing score_lead (scored)...")
    session = AsyncMock()
    
    # Premium private practice lead
    lead = Lead(
        name="Косметолог Анна Иванова",
        website="http://instagram.com/artist",
        phone="whatsapp: +79998887766",
        category="косметолог",
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
    # category_bonuses "косметолог" (15)
    # name_bonuses "косметолог" in name (8)
    # Total score should be 10 + 1 + 15 + 3 + 10 + 5 + 5 + 1 + 15 + 8 = 73
    assert score == 73.0
    assert lead.score == 73.0
    assert lead.status == LeadStatus.SCORED
    print("score_lead (scored) test passed successfully!")


async def main():
    test_load_scoring_rules()
    await test_score_lead_rejected()
    await test_score_lead_scored()
    print("All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
