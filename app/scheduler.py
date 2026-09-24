import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import load_config
from app.services.scanner import scan_all_products
from app.services.second_hand_scanner import scan_second_hand


logger = logging.getLogger("paxscraper")


def run_scan_sync():
    try:
        asyncio.run(scan_all_products())
    except Exception:
        logger.exception(
            "Scheduled price scan failed"
        )


def run_second_hand_sync():
    try:
        asyncio.run(scan_second_hand())
    except Exception:
        logger.exception(
            "Scheduled Second Chance scan failed"
        )


def start_scheduler():
    config = load_config()

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        run_scan_sync,
        trigger="interval",
        hours=6,
        id="ikea_price_scan",
        replace_existing=True,
    )

    if config.second_hand.enabled:
        scheduler.add_job(
            run_second_hand_sync,
            trigger="interval",
            hours=(
                config.second_hand
                .scan_interval_hours
            ),
            id="ikea_second_hand_scan",
            replace_existing=True,
        )

    scheduler.start()

    logger.info(
        "Scheduler started | "
        "normal prices every 6h | "
        "Second Chance every %dh",
        config.second_hand.scan_interval_hours,
    )

    return scheduler