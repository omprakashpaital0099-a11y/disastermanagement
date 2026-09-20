from datetime import datetime, timezone
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.db import SessionLocal
from app.services import cpcb, cwc, firms, imd

scheduler = AsyncIOScheduler(timezone="UTC")


async def run_source(source_name: str, ingest_function) -> None:
    async with SessionLocal() as session:
        try:
            await ingest_function(session)
        except Exception:
            logging.getLogger("prithvinet.scheduler").exception("source=%s status=job_failed", source_name)


def start_scheduler() -> None:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    jobs = []
    providers = [
        ("cwc", cwc.ingest, settings.cwc_api_url, settings.cwc_api_key, settings.cwc_interval_minutes),
        ("imd", imd.ingest, settings.imd_api_url, settings.imd_api_key, settings.imd_interval_minutes),
        ("nasa-firms", firms.ingest, settings.firms_api_url, settings.firms_api_key, settings.firms_interval_minutes),
        ("cpcb", cpcb.ingest, settings.cpcb_api_url, settings.cpcb_api_key, settings.cpcb_interval_minutes),
    ]
    for source_name, ingest_function, url, api_key, interval_minutes in providers:
        if "example.invalid" in url or not api_key:
            continue
        jobs.append((source_name, ingest_function, interval_minutes))
    for source_name, ingest_function, interval_minutes in jobs:
        scheduler.add_job(run_source, "interval", minutes=interval_minutes, args=[source_name, ingest_function], id=f"ingest-{source_name}", replace_existing=True, max_instances=1, next_run_time=now)
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
