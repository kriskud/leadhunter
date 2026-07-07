"""Background workers for the lead processing pipeline."""

import asyncio
import logging

from app.collector import collect_leads
from app.database.session import async_session_factory
from app.enricher import enrich_lead
from app.message_builder import generate_message
from app.qualifier import qualify_lead
from app.scorer import score_lead

logger = logging.getLogger(__name__)


async def collect_worker(*, city: str, category: str, limit: int = 50) -> None:
    """Worker: collect leads from external sources."""
    async with async_session_factory() as session:
        try:
            leads = await collect_leads(session, city=city, category=category, limit=limit)
            await session.commit()
            logger.info("collect_worker: saved %d leads", len(leads))
        except Exception:
            await session.rollback()
            raise


async def enrich_worker(lead_id: int) -> None:
    """Worker: enrich a single lead by ID."""
    async with async_session_factory() as session:
        try:
            from sqlalchemy import select

            from app.database.models import Lead

            result = await session.execute(select(Lead).where(Lead.id == lead_id))
            lead = result.scalar_one_or_none()
            if lead is None:
                logger.error("enrich_worker: lead %s not found", lead_id)
                return
            await enrich_lead(session, lead)
            await session.commit()
        except NotImplementedError:
            logger.warning("enrich_worker: not implemented yet")
        except Exception:
            await session.rollback()
            raise


async def qualify_worker(lead_id: int) -> None:
    """Worker: qualify a single lead by ID."""
    async with async_session_factory() as session:
        try:
            from sqlalchemy import select

            from app.database.models import Lead

            result = await session.execute(select(Lead).where(Lead.id == lead_id))
            lead = result.scalar_one_or_none()
            if lead is None:
                logger.error("qualify_worker: lead %s not found", lead_id)
                return
            await qualify_lead(session, lead)
            await session.commit()
        except NotImplementedError:
            logger.warning("qualify_worker: not implemented yet")
        except Exception:
            await session.rollback()
            raise


async def score_worker(lead_id: int) -> None:
    """Worker: score a single lead by ID."""
    async with async_session_factory() as session:
        try:
            from sqlalchemy import select

            from app.database.models import Lead

            result = await session.execute(select(Lead).where(Lead.id == lead_id))
            lead = result.scalar_one_or_none()
            if lead is None:
                logger.error("score_worker: lead %s not found", lead_id)
                return
            await score_lead(session, lead)
            await session.commit()
        except NotImplementedError:
            logger.warning("score_worker: not implemented yet")
        except Exception:
            await session.rollback()
            raise


async def message_worker(lead_id: int) -> None:
    """Worker: generate outreach message for a single lead by ID."""
    async with async_session_factory() as session:
        try:
            from sqlalchemy import select

            from app.database.models import Lead

            result = await session.execute(select(Lead).where(Lead.id == lead_id))
            lead = result.scalar_one_or_none()
            if lead is None:
                logger.error("message_worker: lead %s not found", lead_id)
                return
            await generate_message(session, lead)
            await session.commit()
        except NotImplementedError:
            logger.warning("message_worker: not implemented yet")
        except Exception:
            await session.rollback()
            raise


def run_worker(coro) -> None:
    """Entry point for CLI-based worker execution."""
    asyncio.run(coro)
