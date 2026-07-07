"""Google Maps lead collector — Playwright-based scraping."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import quote_plus

from playwright.async_api import Browser, Page, async_playwright
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.database.base import LeadStatus
from app.database.models import Lead
from app.database.session import async_session_factory

logger = logging.getLogger(__name__)

SOURCE = "google_maps"

CONSENT_SELECTORS = [
    'button:has-text("Accept all")',
    'button:has-text("Принять все")',
    'button:has-text("Reject all")',
    'button:has-text("Отклонить все")',
    'form[action*="consent"] button',
]

FEED_SELECTOR = 'div[role="feed"]'
PLACE_LINK_SELECTOR = f'{FEED_SELECTOR} a[href*="/maps/place/"]'


@dataclass(frozen=True)
class ScrapedLead:
    name: str
    website: str | None
    phone: str | None


def _build_search_url(category: str, city: str) -> str:
    query = quote_plus(f"{category} {city}")
    return f"https://www.google.com/maps/search/{query}"


def _normalize_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = re.sub(r"[^\d+]", "", raw.strip())
    return cleaned or None


def _normalize_website(raw: str | None) -> str | None:
    if not raw:
        return None
    url = raw.strip()
    if url.startswith("//"):
        url = f"https:{url}"
    return url or None


async def _dismiss_consent(page: Page) -> None:
    for selector in CONSENT_SELECTORS:
        button = page.locator(selector).first
        if await button.count() > 0 and await button.is_visible():
            logger.info("Dismissing consent dialog")
            await button.click()
            await page.wait_for_timeout(1000)
            return


async def _scroll_feed(page: Page) -> None:
    await page.evaluate(
        """() => {
            const feed = document.querySelector('div[role="feed"]');
            if (feed) feed.scrollTop = feed.scrollHeight;
        }"""
    )
    await page.wait_for_timeout(1500)


async def _extract_name(page: Page) -> str | None:
    for selector in ("h1.DUwDvf", "h1"):
        heading = page.locator(selector).first
        if await heading.count() > 0:
            text = (await heading.inner_text()).strip()
            if text:
                return text
    return None


async def _extract_phone(page: Page) -> str | None:
    phone_button = page.locator('[data-item-id^="phone:tel:"]').first
    if await phone_button.count() > 0:
        item_id = await phone_button.get_attribute("data-item-id")
        if item_id and item_id.startswith("phone:tel:"):
            return _normalize_phone(item_id.removeprefix("phone:tel:"))

    for selector in (
        'button[aria-label*="Phone"]',
        'button[aria-label*="Телефон"]',
        'button[aria-label*="phone"]',
        'a[href^="tel:"]',
    ):
        element = page.locator(selector).first
        if await element.count() == 0:
            continue
        href = await element.get_attribute("href")
        if href and href.startswith("tel:"):
            return _normalize_phone(href.removeprefix("tel:"))
        aria = await element.get_attribute("aria-label")
        if aria:
            match = re.search(r"[\d\s()+-]{7,}", aria)
            if match:
                return _normalize_phone(match.group())

    return None


async def _extract_website(page: Page) -> str | None:
    for selector in (
        'a[data-item-id="authority"]',
        'a[aria-label*="Website"]',
        'a[aria-label*="Сайт"]',
        'a[aria-label*="website"]',
    ):
        link = page.locator(selector).first
        if await link.count() > 0:
            href = await link.get_attribute("href")
            normalized = _normalize_website(href)
            if normalized and "google.com" not in normalized:
                return normalized
    return None


async def _extract_place_details(page: Page) -> ScrapedLead | None:
    await page.wait_for_timeout(1200)

    name = await _extract_name(page)
    if not name:
        logger.debug("Skipping place — name not found")
        return None

    phone = await _extract_phone(page)
    website = await _extract_website(page)

    return ScrapedLead(name=name, website=website, phone=phone)


async def _collect_place_links(page: Page, limit: int) -> list[str]:
    """Scroll feed and collect unique place URLs."""
    seen: set[str] = set()
    links: list[str] = []
    stagnant_rounds = 0
    max_stagnant = 5

    while len(links) < limit and stagnant_rounds < max_stagnant:
        elements = page.locator(PLACE_LINK_SELECTOR)
        count = await elements.count()
        before = len(seen)

        for idx in range(count):
            href = await elements.nth(idx).get_attribute("href")
            if not href or href in seen:
                continue
            seen.add(href)
            links.append(href)
            if len(links) >= limit:
                break

        if len(seen) == before:
            stagnant_rounds += 1
        else:
            stagnant_rounds = 0

        if len(links) >= limit:
            break

        await _scroll_feed(page)

    logger.info("Collected %d unique place links", len(links))
    return links[:limit]


async def _scrape_places(page: Page, place_links: list[str]) -> list[ScrapedLead]:
    leads: list[ScrapedLead] = []

    for index, link in enumerate(place_links, start=1):
        logger.info("Scraping place %d/%d", index, len(place_links))
        try:
            await page.goto(link, wait_until="domcontentloaded", timeout=30_000)
            scraped = await _extract_place_details(page)
            if scraped:
                leads.append(scraped)
                logger.info(
                    "Found lead: name=%r phone=%s website=%s",
                    scraped.name,
                    scraped.phone or "—",
                    scraped.website or "—",
                )
        except Exception:
            logger.exception("Failed to scrape place: %s", link)

    return leads


async def _scrape_google_maps(category: str, city: str, limit: int) -> list[ScrapedLead]:
    search_url = _build_search_url(category, city)
    logger.info(
        "Starting Google Maps scrape: category=%r city=%r limit=%d url=%s",
        category,
        city,
        limit,
        search_url,
    )

    async with async_playwright() as playwright:
        browser: Browser = await playwright.chromium.launch(
            headless=settings.playwright_headless,
        )
        context = await browser.new_context(
            locale="ru-RU",
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60_000)
            await _dismiss_consent(page)

            feed = page.locator(FEED_SELECTOR)
            await feed.wait_for(state="visible", timeout=30_000)
            await page.wait_for_timeout(2000)

            place_links = await _collect_place_links(page, limit)
            if not place_links:
                logger.warning("No places found for category=%r city=%r", category, city)
                return []

            return await _scrape_places(page, place_links)
        finally:
            await context.close()
            await browser.close()


def _lead_key(name: str, phone: str | None, city: str) -> tuple[str, str | None, str]:
    return (name.strip().lower(), phone, city.strip().lower())


async def _persist_leads(
    session: AsyncSession,
    scraped: list[ScrapedLead],
    *,
    category: str,
    city: str,
) -> list[Lead]:
    if not scraped:
        return []

    existing = await session.execute(
        select(Lead).where(Lead.source == SOURCE, Lead.city == city)
    )
    existing_keys = {
        _lead_key(lead.name, lead.phone, city)
        for lead in existing.scalars().all()
    }

    saved: list[Lead] = []
    skipped = 0

    for item in scraped:
        key = _lead_key(item.name, item.phone, city)
        if key in existing_keys:
            skipped += 1
            logger.debug("Skipping duplicate lead: %r", item.name)
            continue

        lead = Lead(
            name=item.name,
            website=item.website,
            phone=item.phone,
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
        "Persisted %d leads, skipped %d duplicates (category=%r city=%r)",
        len(saved),
        skipped,
        category,
        city,
    )
    return saved


async def collect_google_maps(
    category: str,
    city: str,
    limit: int = 50,
    *,
    session: AsyncSession | None = None,
) -> list[Lead]:
    """
    Collect leads from Google Maps and save them to PostgreSQL.

    Args:
        category: Business category, e.g. "психолог".
        city: Target city, e.g. "Санкт-Петербург".
        limit: Maximum number of places to scrape.
        session: Optional SQLAlchemy session. Commits internally if not provided.

    Returns:
        List of newly saved Lead records.
    """
    scraped = await _scrape_google_maps(category, city, limit)

    if session is not None:
        return await _persist_leads(session, scraped, category=category, city=city)

    async with async_session_factory() as own_session:
        leads = await _persist_leads(own_session, scraped, category=category, city=city)
        await own_session.commit()
        for lead in leads:
            await own_session.refresh(lead)
        return leads
