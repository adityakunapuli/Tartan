import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.core.database import get_db, engine
from sqlmodel import Session
from backend.modules.plaid_integration.sync import run_sync
from backend.modules.analytics.categorizer import run_categorization

logger = logging.getLogger(__name__)

# Initialize APScheduler
scheduler = AsyncIOScheduler()

def automated_sync_job():
    """Job to run the Plaid sync and subsequent categorization."""
    logger.info("Running scheduled Plaid Sync...")
    try:
        run_sync()
        logger.info("Running scheduled Categorization...")
        run_categorization()
        logger.info("Scheduled job completed successfully.")
    except Exception as e:
        logger.error(f"Error during scheduled sync: {e}")

def start_scheduler():
    """Starts the background scheduler."""
    # Here we can add dynamic logic to run based on Account.sync_interval_hours,
    # but for a simple start, let's run it once every 24 hours.
    # To run varying frequencies, we'd query the DB for accounts and schedule them individually.
    # For now, we will just sync all items every 12 hours.
    
    scheduler.add_job(
        automated_sync_job,
        trigger=IntervalTrigger(hours=12),
        id="automated_plaid_sync",
        name="Automated Plaid Sync and Categorization",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started. Automated sync scheduled.")

def stop_scheduler():
    """Stops the scheduler."""
    scheduler.shutdown()
    logger.info("APScheduler stopped.")
