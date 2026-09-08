from dataclasses import dataclass

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.ikea import fetch_product_price
from app.models import PriceObservation, Product


@dataclass
class PriceCheckResult:
    article_number: str
    previous_price: float | None
    current_price: float
    changed: bool
    dropped: bool


async def check_product_price(
    db: Session,
    product: Product,
) -> PriceCheckResult:
    current_price = await fetch_product_price(product.url)

    previous_observation = db.scalar(
        select(PriceObservation)
        .where(PriceObservation.product_id == product.id)
        .order_by(desc(PriceObservation.checked_at))
        .limit(1)
    )

    # First ever observation
    if previous_observation is None:
        db.add(
            PriceObservation(
                product_id=product.id,
                price=current_price,
            )
        )
        db.commit()

        return PriceCheckResult(
            article_number=product.article_number,
            previous_price=None,
            current_price=current_price,
            changed=True,
            dropped=False,
        )

    previous_price = previous_observation.price

    # Nothing changed, so don't create a new row
    if current_price == previous_price:
        return PriceCheckResult(
            article_number=product.article_number,
            previous_price=previous_price,
            current_price=current_price,
            changed=False,
            dropped=False,
        )

    # Price changed, so record it
    db.add(
        PriceObservation(
            product_id=product.id,
            price=current_price,
        )
    )
    db.commit()

    return PriceCheckResult(
        article_number=product.article_number,
        previous_price=previous_price,
        current_price=current_price,
        changed=True,
        dropped=current_price < previous_price,
    )