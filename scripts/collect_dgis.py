"""CLI: сбор лидов из 2GIS. PYTHONPATH=. .venv/bin/python scripts/collect_dgis.py "косметолог" "Москва" --limit 100"""

import argparse
import asyncio
import logging

from app.collector.dgis import collect_dgis


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect leads from 2GIS Places API")
    parser.add_argument("category", help='Категория, напр. "косметолог"')
    parser.add_argument("city", help='Город, напр. "Москва"')
    parser.add_argument("--limit", type=int, default=100, help="Максимум мест")
    parser.add_argument("--max-branches", type=int, default=2, help="Отсекать организации с бОльшим числом филиалов")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    leads = asyncio.run(collect_dgis(args.category, args.city, args.limit, max_branches=args.max_branches))
    print(f"Saved {len(leads)} leads")
    for lead in leads:
        print(f"  [{lead.id}] {lead.name} | {lead.phone or '—'} | {lead.website or '—'}")


if __name__ == "__main__":
    main()
