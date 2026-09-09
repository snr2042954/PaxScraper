import logging
import os

from dotenv import load_dotenv

from app.config import load_products
from app.db import SessionLocal
from app.ikea import fetch_product
from app.services.notifier import send_pushover_notification
from app.services.price_checker import check_product_price


load_dotenv()

logger = logging.getLogger("paxscraper")

PRICE_CHANGE_THRESHOLD_PERCENT = float(
    os.getenv(
        "PRICE_CHANGE_THRESHOLD_PERCENT",
        "5",
    )
)


async def scan_all_products() -> None:
    tracked_products = load_products()

    logger.info(
        "Starting IKEA price scan for %d products",
        len(tracked_products),
    )

    successful = 0
    failed = 0

    with SessionLocal() as db:
        for tracked in tracked_products:
            try:
                product = await fetch_product(
                    tracked.url
                )

                result = check_product_price(
                    db,
                    product,
                )

                successful += 1

                # First observation
                if result.previous_price is None:
                    logger.info(
                        "SCAN OK | %s | %s | €%.2f | baseline",
                        product.article_number,
                        product.name,
                        product.price,
                    )

                    continue

                # Price unchanged
                if not result.changed:
                    logger.info(
                        "SCAN OK | %s | %s | €%.2f | unchanged",
                        product.article_number,
                        product.name,
                        product.price,
                    )

                    continue

                # Price changed
                percentage_change = (
                    (
                        result.current_price
                        - result.previous_price
                    )
                    / result.previous_price
                    * 100
                )

                logger.info(
                    "SCAN OK | %s | %s | €%.2f -> €%.2f | %+.2f%%",
                    product.article_number,
                    product.name,
                    result.previous_price,
                    result.current_price,
                    percentage_change,
                )

                # Notify for changes greater than configured threshold
                if abs(percentage_change) > PRICE_CHANGE_THRESHOLD_PERCENT:

                    direction = (
                        "PRICE DROP"
                        if percentage_change < 0
                        else "PRICE INCREASE"
                    )

                    message = (
                        f"{product.name}\n"
                        f"Article: {product.article_number}\n\n"
                        f"€{result.previous_price:.2f} → "
                        f"€{result.current_price:.2f}\n"
                        f"{percentage_change:+.1f}%"
                    )

                    try:
                        await send_pushover_notification(
                            title=f"{direction}: {product.name}",
                            message=message,
                            url=product.url,
                        )

                        logger.info(
                            "PUSHOVER SENT | %s | %+.2f%%",
                            product.article_number,
                            percentage_change,
                        )

                    except Exception:
                        logger.exception(
                            "PUSHOVER FAILED | %s",
                            product.article_number,
                        )

            except Exception:
                failed += 1

                logger.exception(
                    "SCAN FAILED | %s",
                    tracked.url,
                )

    logger.info(
        "IKEA price scan finished | successful=%d failed=%d",
        successful,
        failed,
    )