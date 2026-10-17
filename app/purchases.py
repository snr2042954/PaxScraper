from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Purchase


def get_purchased_quantity(
    db: Session,
    article_number: str,
) -> int:
    quantity = db.scalar(
        select(
            func.coalesce(
                func.sum(Purchase.quantity),
                0,
            )
        )
        .where(
            Purchase.article_number
            == article_number
        )
    )

    return int(quantity or 0)


def product_is_complete(
    db: Session,
    article_number: str,
    quantity_needed: int,
) -> bool:
    return (
        get_purchased_quantity(
            db,
            article_number,
        )
        >= quantity_needed
    )