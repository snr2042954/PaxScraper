import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import load_config
from app.db import SessionLocal
from app.ikea import extract_article_number
from app.models import SecondHandOfferRecord
from app.purchases import product_is_complete
from app.second_hand import (
    fetch_second_hand_store,
    resolve_store_ids,
)
from app.services.notifier import (
    send_pushover_notification,
)


logger = logging.getLogger(
    "paxscraper"
)


async def scan_second_hand() -> None:
    config = load_config()

    if not config.second_hand.enabled:
        logger.info(
            "Second Chance scanning disabled"
        )
        return

    logger.info(
        "Starting Second Chance scan | "
        "stores=%d products=%d",
        len(config.second_hand.stores),
        len(config.products),
    )

    total_matches = 0
    new_notifications = 0

    store_ids = await resolve_store_ids(
        config.second_hand.stores
    )

    if not store_ids:
        logger.warning(
            "No Second Chance stores "
            "could be resolved"
        )
        return

    with SessionLocal() as db:

        # Only include products we still need.
        tracked_articles = set()

        for tracked in config.products:
            article_number = (
                extract_article_number(
                    tracked.url
                )
            )

            if not product_is_complete(
                db,
                article_number,
                tracked.quantity_needed,
            ):
                tracked_articles.add(
                    article_number
                )

        logger.info(
            "Second Chance active tracking | "
            "articles=%d",
            len(tracked_articles),
        )

        for (
            store_name,
            store_id,
        ) in store_ids.items():

            try:
                offers = (
                    await fetch_second_hand_store(
                        store_id
                    )
                )

                matching_offers = [
                    offer
                    for offer in offers
                    if (
                        offer.article_number
                        in tracked_articles
                    )
                ]

                total_matches += len(
                    matching_offers
                )

                logger.info(
                    "SECOND HAND STORE OK | "
                    "%s | offers=%d matches=%d",
                    store_name,
                    len(offers),
                    len(matching_offers),
                )

                now = datetime.now(
                    timezone.utc
                )

                current_offer_uuids = {
                    offer.offer_uuid
                    for offer in matching_offers
                }

                active_records = db.scalars(
                    select(
                        SecondHandOfferRecord
                    )
                    .where(
                        SecondHandOfferRecord.store_id
                        == store_id,
                        SecondHandOfferRecord.active
                        .is_(True),
                    )
                ).all()

                for record in active_records:
                    if (
                        record.offer_uuid
                        not in current_offer_uuids
                    ):
                        record.active = False

                        logger.info(
                            "SECOND HAND GONE | "
                            "%s | %s | %s",
                            store_name,
                            record.article_number,
                            record.offer_uuid,
                        )

                notification_candidates = []

                for offer in matching_offers:

                    record = db.get(
                        SecondHandOfferRecord,
                        offer.offer_uuid,
                    )

                    if record is None:
                        record = (
                            SecondHandOfferRecord(
                                offer_uuid=(
                                    offer.offer_uuid
                                ),
                                article_number=(
                                    offer.article_number
                                ),
                                store_id=(
                                    offer.store_id
                                ),
                                store_name=(
                                    store_name
                                ),
                                title=offer.title,
                                description=(
                                    offer.description
                                ),
                                original_price=(
                                    offer.original_price
                                ),
                                price=offer.price,
                                condition_code=(
                                    offer.condition_code
                                ),
                                condition_title=(
                                    offer.condition_title
                                ),
                                reason_discount=(
                                    offer.reason_discount
                                ),
                                additional_info=(
                                    offer.additional_info
                                ),
                                active=True,
                                first_seen_at=now,
                                last_seen_at=now,
                            )
                        )

                        db.add(record)

                    else:
                        record.article_number = (
                            offer.article_number
                        )

                        record.store_id = (
                            offer.store_id
                        )

                        record.store_name = (
                            store_name
                        )

                        record.title = (
                            offer.title
                        )

                        record.description = (
                            offer.description
                        )

                        record.original_price = (
                            offer.original_price
                        )

                        record.price = (
                            offer.price
                        )

                        record.condition_code = (
                            offer.condition_code
                        )

                        record.condition_title = (
                            offer.condition_title
                        )

                        record.reason_discount = (
                            offer.reason_discount
                        )

                        record.additional_info = (
                            offer.additional_info
                        )

                        record.active = True
                        record.last_seen_at = now

                    if offer.original_price > 0:
                        discount = (
                            (
                                offer.original_price
                                - offer.price
                            )
                            / offer.original_price
                            * 100
                        )

                    else:
                        discount = 0

                    if (
                        discount
                        >= config.second_hand
                        .min_discount_percent
                        and record.notified_at
                        is None
                    ):
                        notification_candidates.append(
                            (
                                record,
                                offer,
                                discount,
                            )
                        )

                db.commit()

                for (
                    record,
                    offer,
                    discount,
                ) in notification_candidates:

                    message = (
                        f"{offer.title}\n"
                        f"{offer.description}\n\n"
                        f"Article: "
                        f"{offer.article_number}\n"
                        f"Store: "
                        f"{store_name.title()}\n\n"
                        f"Retail: "
                        f"€{offer.original_price:.2f}\n"
                        f"Second Chance: "
                        f"€{offer.price:.2f}\n"
                        f"Discount: "
                        f"{discount:.1f}%\n\n"
                        f"Condition: "
                        f"{offer.condition_title or '-'}\n"
                        f"Reason: "
                        f"{offer.reason_discount or '-'}"
                    )

                    if offer.additional_info:
                        message += (
                            "\nInfo: "
                            f"{offer.additional_info}"
                        )

                    try:
                        await (
                            send_pushover_notification(
                                title=(
                                    "Second Chance: "
                                    f"{offer.title}"
                                ),
                                message=message,
                                url=(
                                    "https://www.ikea.com/"
                                    "nl/nl/circular/"
                                    "second-hand/"
                                    f"#/{store_name}"
                                ),
                            )
                        )

                        record.notified_at = (
                            datetime.now(
                                timezone.utc
                            )
                        )

                        db.commit()

                        new_notifications += 1

                        logger.info(
                            "SECOND HAND MATCH | "
                            "%s | %s | "
                            "€%.2f -> €%.2f | "
                            "%.1f%%",
                            store_name,
                            offer.article_number,
                            offer.original_price,
                            offer.price,
                            discount,
                        )

                    except Exception:
                        logger.exception(
                            "SECOND HAND PUSHOVER "
                            "FAILED | %s | %s",
                            store_name,
                            offer.article_number,
                        )

            except Exception:
                logger.exception(
                    "SECOND HAND STORE FAILED | %s",
                    store_name,
                )

    logger.info(
        "Second Chance scan finished | "
        "matches=%d notifications=%d",
        total_matches,
        new_notifications,
    )