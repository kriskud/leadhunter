"""Пере-скоринг лидов в базе: PYTHONPATH=. .venv/bin/python scripts/score_leads.py [--category косметолог]"""

import argparse
import asyncio

from sqlalchemy import select

from app.database.base import LeadStatus
from app.database.models import Lead
from app.database.session import async_session_factory
from app.scorer import score_lead


async def run(category: str | None) -> None:
    async with async_session_factory() as session:
        query = select(Lead)
        if category:
            query = query.where(Lead.category == category)
        leads = (await session.execute(query)).scalars().all()

        scored = 0
        for lead in leads:
            await score_lead(session, lead)
            if lead.status == LeadStatus.SCORED:
                scored += 1
        await session.commit()

    print(f"Scored {len(leads)} leads: {scored} SCORED, {len(leads) - scored} REJECTED")


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-score leads against current scoring rules")
    parser.add_argument("--category", default=None)
    args = parser.parse_args()
    asyncio.run(run(args.category))


if __name__ == "__main__":
    main()
