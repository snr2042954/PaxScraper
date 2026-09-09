import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.scanner import scan_all_products


logger = logging.getLogger("paxscraper")


def run_scan_sync():
    try:
        asyncio.run(scan_all_products())
    except Exception:
        logger.exception("Scheduled scan failed")


def start_scheduler():
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        run_scan_sync,
        trigger="interval",
        hours=6,
        id="ikea_price_scan",
        replace_existing=True,
    )

    scheduler.start()

    logger.info(
        "Scheduler started. IKEA prices will be scanned every 6 hours."
    )

    return scheduler