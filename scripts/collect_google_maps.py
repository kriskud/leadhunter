"""CLI entry point for Google Maps lead collection."""

import argparse
import asyncio
import logging

from app.collector.google_maps import collect_google_maps


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect leads from Google Maps")
    parser.add_argument("category", help='Business category, e.g. "психолог"')
    parser.add_argument("city", help='Target city, e.g. "Санкт-Петербург"')
    parser.add_argument("--limit", type=int, default=50, help="Max places to scrape")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    leads = asyncio.run(collect_google_maps(args.category, args.city, args.limit))
    print(f"Saved {len(leads)} leads")
    for lead in leads:
        print(f"  [{lead.id}] {lead.name} | {lead.phone or '—'} | {lead.website or '—'}")


if __name__ == "__main__":
    main()
