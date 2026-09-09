import asyncio
import logging
import time
import json
import re
from urllib.parse import quote_plus
from playwright.async_api import Browser, Page, async_playwright

# Setup Logger to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("maps_poc")

CONSENT_SELECTORS = [
    'button:has-text("Accept all")',
    'button:has-text("Принять все")',
    'button:has-text("Reject all")',
    'button:has-text("Отклонить все")',
    'form[action*="consent"] button',
]

FEED_SELECTOR = 'div[role="feed"]'
PLACE_LINK_SELECTOR = f'{FEED_SELECTOR} a[href*="/maps/place/"]'

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
    logger.info("Checking for consent dialogs...")
    for selector in CONSENT_SELECTORS:
        button = page.locator(selector).first
        if await button.count() > 0 and await button.is_visible():
            logger.info(f"Dismissing consent dialog via selector: {selector}")
            await button.click()
            await page.wait_for_timeout(2000)
            return

async def _scroll_feed(page: Page) -> None:
    logger.info("Scrolling the feed to load more places...")
    await page.evaluate(
        """() => {
            const feed = document.querySelector('div[role="feed"]');
            if (feed) feed.scrollTop = feed.scrollHeight;
        }"""
    )
    await page.wait_for_timeout(2000)

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

async def run_poc():
    category = "косметолог"
    city = "Москва"
    limit = 35 # 30-50 карточек
    
    start_time = time.time()
    search_url = _build_search_url(category, city)
    logger.info(f"Starting POC: category={category!r} city={city!r} url={search_url}")
    
    results = []
    stats = {
        "found_links": 0,
        "scraped_count": 0,
        "errors": 0,
        "captcha_encountered": False,
        "final_step": "init"
    }

    async with async_playwright() as playwright:
        logger.info("Launching chromium...")
        browser: Browser = await playwright.chromium.launch(
            headless=True,
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
            logger.info(f"Navigating to {search_url}...")
            stats["final_step"] = "navigating_to_search"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60_000)
            
            # Check for generic Google captcha or redirects
            title = await page.title()
            logger.info(f"Page title: {title}")
            content = await page.content()
            if "captcha" in content.lower() or "sorry" in content.lower():
                logger.error("CAPTCHA detected immediately on initial page load!")
                stats["captcha_encountered"] = True
                stats["final_step"] = "captcha_on_init"
                return results, stats

            await _dismiss_consent(page)
            
            stats["final_step"] = "waiting_for_feed"
            feed = page.locator(FEED_SELECTOR)
            try:
                await feed.wait_for(state="visible", timeout=20_000)
            except Exception as e:
                logger.error(f"Feed selector {FEED_SELECTOR} not found or not visible: {e}")
                # Log if there is some other visible content or potential block screen
                stats["final_step"] = "failed_feed_visibility"
                return results, stats

            await page.wait_for_timeout(2000)

            # Collect unique place URLs
            logger.info("Starting link collection...")
            stats["final_step"] = "collecting_links"
            seen: set[str] = set()
            links: list[str] = []
            stagnant_rounds = 0
            max_stagnant = 12 # higher tolerance for loading

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

                logger.info(f"Collected {len(links)} links so far (stagnant rounds: {stagnant_rounds})")

                if len(seen) == before:
                    stagnant_rounds += 1
                else:
                    stagnant_rounds = 0

                if len(links) >= limit:
                    break

                await _scroll_feed(page)

            stats["found_links"] = len(links)
            logger.info(f"Finished link collection. Found {len(links)} unique place links.")

            if not links:
                logger.warning("No place links collected. Exiting.")
                stats["final_step"] = "no_links_collected"
                return results, stats

            # Scrape details from collected links
            stats["final_step"] = "scraping_details"
            for index, link in enumerate(links, start=1):
                logger.info(f"Scraping place {index}/{len(links)}: {link}")
                try:
                    await page.goto(link, wait_until="domcontentloaded", timeout=20_000)
                    
                    # Verify if captcha page gets loaded instead
                    detail_content = await page.content()
                    if "captcha" in detail_content.lower() or "sorry" in detail_content.lower():
                        logger.error("CAPTCHA detected during details extraction!")
                        stats["captcha_encountered"] = True
                        stats["final_step"] = f"captcha_at_place_{index}"
                        break
                    
                    await page.wait_for_timeout(1500)
                    name = await _extract_name(page)
                    if not name:
                        logger.warning(f"Could not extract name for {link}")
                        stats["errors"] += 1
                        continue
                    
                    phone = await _extract_phone(page)
                    website = await _extract_website(page)
                    
                    item = {
                        "name": name,
                        "phone": phone,
                        "website": website,
                        "link": link
                    }
                    results.append(item)
                    stats["scraped_count"] += 1
                    logger.info(f"Successfully scraped: {name} | Phone: {phone} | Website: {website}")
                except Exception as e:
                    logger.error(f"Error scraping place {link}: {e}")
                    stats["errors"] += 1

            if stats["scraped_count"] == len(links):
                stats["final_step"] = "success"

        except Exception as e:
            logger.exception(f"Global POC execution error: {e}")
            stats["final_step"] = f"error_{type(e).__name__}"
        finally:
            await context.close()
            await browser.close()

    duration = time.time() - start_time
    stats["duration_seconds"] = round(duration, 2)
    return results, stats

if __name__ == "__main__":
    results, stats = asyncio.run(run_poc())
    print("\n" + "="*50)
    print("POC RESULTS")
    print("="*50)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print("\n" + "="*50)
    print("POC STATS")
    print("="*50)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print("="*50)
