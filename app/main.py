from contextlib import asynccontextmanager
import logging
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, desc, select

from app.config import load_products
from app.db import (
    Base,
    SessionLocal,
    engine,
)
from app.ikea import extract_article_number
from app.models import (
    PriceObservation,
    ProductMetadata,
    Purchase,
    SecondHandOfferRecord,
)
from app.scheduler import start_scheduler
from app.services.scanner import (
    scan_all_products,
)
from app.services.second_hand_scanner import (
    scan_second_hand,
)


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    ),
    force=True,
)

logger = logging.getLogger(
    "paxscraper"
)

logger.setLevel(
    logging.INFO
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = start_scheduler()

    logger.info(
        "PAX Scraper started"
    )

    yield

    scheduler.shutdown()

    logger.info(
        "PAX Scraper stopped"
    )


app = FastAPI(
    title="PAX Scraper",
    lifespan=lifespan,
)


app.mount(
    "/static",
    StaticFiles(
        directory=(
            Path(__file__).parent
            / "static"
        )
    ),
    name="static",
)


Base.metadata.create_all(
    bind=engine
)


templates = Jinja2Templates(
    directory=str(
        Path(__file__).parent
        / "templates"
    )
)


@app.get("/")
def dashboard(
    request: Request,
):
    tracked_products = (
        load_products()
    )

    dashboard_products = []

    with SessionLocal() as db:

        for tracked in tracked_products:

            article_number = (
                extract_article_number(
                    tracked.url
                )
            )

            metadata = db.get(
                ProductMetadata,
                article_number,
            )

            observations = db.scalars(
                select(
                    PriceObservation
                )
                .where(
                    PriceObservation.article_number
                    == article_number
                )
                .order_by(
                    desc(
                        PriceObservation.checked_at
                    )
                )
            ).all()

            current_observation = (
                observations[0]
                if observations
                else None
            )

            current_price = (
                current_observation.price
                if current_observation
                else None
            )

            listing_price = None

            if observations:
                listing_price = max(
                    observation.price
                    for observation
                    in observations
                )

            most_recent_discount_price = None

            if listing_price is not None:

                for observation in observations:

                    if (
                        observation.price
                        < listing_price
                    ):
                        most_recent_discount_price = (
                            observation.price
                        )

                        break

            second_hand_offers = db.scalars(
                select(
                    SecondHandOfferRecord
                )
                .where(
                    SecondHandOfferRecord
                    .article_number
                    == article_number,

                    SecondHandOfferRecord
                    .active
                    .is_(True),
                )
                .order_by(
                    SecondHandOfferRecord
                    .price
                    .asc()
                )
            ).all()

            best_second_hand = (
                second_hand_offers[0]
                if second_hand_offers
                else None
            )

            second_hand_discount = None

            if (
                best_second_hand
                and listing_price
                is not None
                and listing_price > 0
            ):
                second_hand_discount = (
                    (
                        listing_price
                        - best_second_hand.price
                    )
                    / listing_price
                    * 100
                )

            # ---------------------------------------------
            # Purchases
            # ---------------------------------------------

            purchases = db.scalars(
                select(
                    Purchase
                )
                .where(
                    Purchase.article_number
                    == article_number
                )
                .order_by(
                    Purchase.purchased_at
                    .asc()
                )
            ).all()

            quantity_bought = sum(
                purchase.quantity
                for purchase in purchases
            )

            purchase_total = sum(
                (
                    purchase.quantity
                    * purchase.unit_price
                )
                for purchase in purchases
            )

            average_bought_price = None

            if quantity_bought > 0:
                average_bought_price = (
                    purchase_total
                    / quantity_bought
                )

            quantity_remaining = max(
                tracked.quantity_needed
                - quantity_bought,
                0,
            )

            completed = (
                quantity_bought
                >= tracked.quantity_needed
            )

            # Realized saving on items actually bought.
            realized_discount = 0.0

            if (
                listing_price is not None
                and quantity_bought > 0
            ):
                realized_discount = (
                    listing_price
                    * quantity_bought
                    - purchase_total
                )

            dashboard_products.append(
                {
                    "article_number":
                    article_number,

                    "name": (
                        metadata.name
                        if metadata
                        else "Unknown product"
                    ),

                    "url":
                    tracked.url,

                    "quantity_needed":
                    tracked.quantity_needed,

                    "current_price":
                    current_price,

                    "listing_price":
                    listing_price,

                    "most_recent_discount_price":
                    most_recent_discount_price,

                    "second_hand_offer":
                    best_second_hand,

                    "second_hand_discount":
                    second_hand_discount,

                    "second_hand_offer_count":
                    len(
                        second_hand_offers
                    ),

                    "quantity_bought":
                    quantity_bought,

                    "quantity_remaining":
                    quantity_remaining,

                    "purchase_total":
                    purchase_total,

                    "average_bought_price":
                    average_bought_price,

                    "realized_discount":
                    realized_discount,

                    "completed":
                    completed,
                }
            )

    # -------------------------------------------------
    # Header statistics
    # -------------------------------------------------

    tracked_count = len(
        dashboard_products
    )

    price_drop_count = sum(
        1
        for product
        in dashboard_products
        if (
            not product["completed"]
            and product[
                "most_recent_discount_price"
            ]
            is not None
        )
    )

    second_hand_match_count = sum(
        1
        for product
        in dashboard_products
        if (
            not product["completed"]
            and product[
                "second_hand_offer"
            ]
            is not None
        )
    )

    # -------------------------------------------------
    # Financial totals
    # -------------------------------------------------

    listing_price_total = sum(
        (
            product[
                "listing_price"
            ]
            * product[
                "quantity_needed"
            ]
        )
        for product
        in dashboard_products
        if (
            product[
                "listing_price"
            ]
            is not None
        )
    )

    # Only savings that have actually been realized
    # through a purchase count here.
    discount_total = sum(
        product[
            "realized_discount"
        ]
        for product
        in dashboard_products
    )

    # Remaining unbought products are assumed to
    # eventually be bought at listing price.
    projected_cost_total = (
        listing_price_total
        - discount_total
    )

    return (
        templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "products":
                dashboard_products,

                "tracked_count":
                tracked_count,

                "price_drop_count":
                price_drop_count,

                "second_hand_match_count":
                second_hand_match_count,

                "listing_price_total":
                listing_price_total,

                "discount_total":
                discount_total,

                "projected_cost_total":
                projected_cost_total,
            },
        )
    )


@app.post(
    "/purchase/{article_number}"
)
async def add_purchase(
    article_number: str,
    request: Request,
):
    body = (
        await request.body()
    ).decode(
        "utf-8"
    )

    form = parse_qs(body)

    try:
        quantity = int(
            form.get(
                "quantity",
                ["1"],
            )[0]
        )

        unit_price = float(
            form.get(
                "unit_price",
                ["0"],
            )[0]
            .replace(
                ",",
                ".",
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return RedirectResponse(
            url="/",
            status_code=303,
        )

    if (
        quantity <= 0
        or unit_price < 0
    ):
        return RedirectResponse(
            url="/",
            status_code=303,
        )

    tracked_products = (
        load_products()
    )

    tracked = next(
        (
            product
            for product
            in tracked_products
            if (
                extract_article_number(
                    product.url
                )
                == article_number
            )
        ),
        None,
    )

    if tracked is None:
        return RedirectResponse(
            url="/",
            status_code=303,
        )

    with SessionLocal() as db:

        purchases = db.scalars(
            select(Purchase)
            .where(
                Purchase.article_number
                == article_number
            )
        ).all()

        already_bought = sum(
            purchase.quantity
            for purchase in purchases
        )

        remaining = max(
            tracked.quantity_needed
            - already_bought,
            0,
        )

        if remaining <= 0:
            return RedirectResponse(
                url="/",
                status_code=303,
            )

        # Never allow the purchase count to exceed
        # the configured requirement.
        quantity = min(
            quantity,
            remaining,
        )

        db.add(
            Purchase(
                article_number=(
                    article_number
                ),
                quantity=quantity,
                unit_price=unit_price,
            )
        )

        db.commit()

    logger.info(
        "PURCHASE ADDED | %s | "
        "quantity=%d | €%.2f",
        article_number,
        quantity,
        unit_price,
    )

    return RedirectResponse(
        url="/",
        status_code=303,
    )


@app.post(
    "/purchase/{article_number}/clear"
)
async def clear_purchases(
    article_number: str,
):
    with SessionLocal() as db:
        db.execute(
            delete(Purchase)
            .where(
                Purchase.article_number
                == article_number
            )
        )

        db.commit()

    logger.info(
        "PURCHASES CLEARED | %s",
        article_number,
    )

    return RedirectResponse(
        url="/",
        status_code=303,
    )


@app.post("/scan")
async def scan():
    logger.info(
        "Manual scan requested"
    )

    await scan_all_products()

    await scan_second_hand()

    return RedirectResponse(
        url="/",
        status_code=303,
    )