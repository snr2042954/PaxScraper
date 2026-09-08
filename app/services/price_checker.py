from dataclasses import dataclass

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.ikea import IkeaProduct
from app.models import PriceObservation


@dataclass
class PriceCheckResult:
    article_number: str
    previous_price: float | None
    current_price: float
    changed: bool
    dropped: bool


def check_product_price(
    db: Session,
    product: IkeaProduct,
) -> PriceCheckResult:

    previous_observation = db.scalar(
        select(PriceObservation)
        .where(
            PriceObservation.article_number
            == product.article_number
        )
        .order_by(desc(PriceObservation.checked_at))
        .limit(1)
    )

    if previous_observation is None:
        db.add(
            PriceObservation(
                article_number=product.article_number,
                price=product.price,
            )
        )

        db.commit()

        return PriceCheckResult(
            article_number=product.article_number,
            previous_price=None,
            current_price=product.price,
            changed=True,
            dropped=False,
        )

    previous_price = previous_observation.price

    if product.price == previous_price:
        return PriceCheckResult(
            article_number=product.article_number,
            previous_price=previous_price,
            current_price=product.price,
            changed=False,
            dropped=False,
        )

    db.add(
        PriceObservation(
            article_number=product.article_number,
            price=product.price,
        )
    )

    db.commit()

    return PriceCheckResult(
        article_number=product.article_number,
        previous_price=previous_price,
        current_price=product.price,
        changed=True,
        dropped=product.price < previous_price,
    )