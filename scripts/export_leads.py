"""Экспорт лидов в CSV: PYTHONPATH=. .venv/bin/python scripts/export_leads.py [--category косметолог] [-o leads.csv]"""

import argparse
import asyncio
import csv
import sys

from sqlalchemy import select

from app.database.models import Lead
from app.database.session import async_session_factory


async def export(category: str | None, out_path: str | None) -> None:
    async with async_session_factory() as session:
        query = select(Lead).order_by(Lead.city, Lead.name)
        if category:
            query = query.where(Lead.category == category)
        leads = (await session.execute(query)).scalars().all()

    out = open(out_path, "w", newline="", encoding="utf-8") if out_path else sys.stdout
    writer = csv.writer(out)
    writer.writerow(["id", "name", "phone", "website", "category", "city", "status", "score"])
    for lead in leads:
        writer.writerow([lead.id, lead.name, lead.phone or "", lead.website or "",
                         lead.category or "", lead.city or "", lead.status.value, lead.score or ""])
    if out_path:
        out.close()
        print(f"Exported {len(leads)} leads to {out_path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export leads to CSV")
    parser.add_argument("--category", default=None)
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    asyncio.run(export(args.category, args.output))


if __name__ == "__main__":
    main()
