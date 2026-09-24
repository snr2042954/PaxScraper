from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select

from app.config import load_products
from app.db import Base, SessionLocal, engine
from app.ikea import extract_article_number
from app.models import (
    PriceObservation,
    ProductMetadata,
    SecondHandOfferRecord,
)
from app.scheduler import start_scheduler
from app.services.scanner import scan_all_products
from app.services.second_hand_scanner import scan_second_hand


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    force=True,
)

logger = logging.getLogger("paxscraper")
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = start_scheduler()

    logger.info("PAX Scraper started")

    yield

    scheduler.shutdown()

    logger.info("PAX Scraper stopped")


app = FastAPI(
    title="PAX Scraper",
    lifespan=lifespan,
)


app.mount(
    "/static",
    StaticFiles(
        directory=Path(__file__).parent / "static"
    ),
    name="static",
)


Base.metadata.create_all(
    bind=engine
)


templates = Jinja2Templates(
    directory=str(
        Path(__file__).parent / "templates"
    )
)


@app.get("/")
def dashboard(request: Request):
    tracked_products = load_products()

    dashboard_products = []

    with SessionLocal() as db:

        for tracked in tracked_products:

            article_number = extract_article_number(
                tracked.url
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
                .limit(2)
            ).all()

            current = (
                observations[0]
                if observations
                else None
            )

            previous = (
                observations[1]
                if len(observations) > 1
                else None
            )

            difference = None
            percentage_change = None

            if current and previous:

                difference = (
                    current.price
                    - previous.price
                )

                if previous.price != 0:
                    percentage_change = (
                        difference
                        / previous.price
                        * 100
                    )

            second_hand_offers = db.scalars(
                select(
                    SecondHandOfferRecord
                )
                .where(
                    SecondHandOfferRecord.article_number
                    == article_number,
                    SecondHandOfferRecord.active.is_(
                        True
                    ),
                )
                .order_by(
                    SecondHandOfferRecord.price.asc()
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
                and best_second_hand.original_price > 0
            ):
                second_hand_discount = (
                    (
                        best_second_hand.original_price
                        - best_second_hand.price
                    )
                    / best_second_hand.original_price
                    * 100
                )

            dashboard_products.append(
                {
                    "article_number": article_number,
                    "name": (
                        metadata.name
                        if metadata
                        else "Unknown product"
                    ),
                    "url": tracked.url,
                    "quantity_needed": (
                        tracked.quantity_needed
                    ),
                    "target_price": (
                        tracked.target_price
                    ),
                    "current_price": (
                        current.price
                        if current
                        else None
                    ),
                    "previous_price": (
                        previous.price
                        if previous
                        else None
                    ),
                    "difference": difference,
                    "percentage_change": (
                        percentage_change
                    ),
                    "last_changed": (
                        current.checked_at
                        if current
                        else None
                    ),
                    "second_hand_offer": (
                        best_second_hand
                    ),
                    "second_hand_discount": (
                        second_hand_discount
                    ),
                    "second_hand_offer_count": (
                        len(
                            second_hand_offers
                        )
                    ),
                }
            )

    scanned_count = sum(
        1
        for product in dashboard_products
        if product["current_price"]
        is not None
    )

    price_drop_count = sum(
        1
        for product in dashboard_products
        if (
            product["difference"]
            is not None
            and product["difference"] < 0
        )
    )

    units_needed = sum(
        product["quantity_needed"]
        for product in dashboard_products
    )

    second_hand_match_count = sum(
        1
        for product in dashboard_products
        if (
            product["second_hand_offer"]
            is not None
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "products": (
                dashboard_products
            ),
            "scanned_count": (
                scanned_count
            ),
            "price_drop_count": (
                price_drop_count
            ),
            "units_needed": (
                units_needed
            ),
            "second_hand_match_count": (
                second_hand_match_count
            ),
        },
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