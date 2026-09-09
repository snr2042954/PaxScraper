import asyncio

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import load_products
from app.db import SessionLocal
from app.ikea import fetch_product
from app.services.price_checker import check_product_price


async def run_scan():
    tracked_products = load_products()

    with SessionLocal() as db:
        for tracked in tracked_products:
            try:
                product = await fetch_product(tracked.url)

                check_product_price(
                    db,
                    product,
                )

                print(
                    f"Scanned {product.article_number}: "
                    f"€{product.price:.2f}"
                )

            except Exception as exc:
                print(
                    f"Error scanning {tracked.url}: {exc}"
                )


def run_scan_sync():
    asyncio.run(run_scan())


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

    return scheduler