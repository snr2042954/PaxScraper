import asyncio

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.ikea import PRODUCT_URL, fetch_product_price
from app.models import PriceObservation, Product


ARTICLE_NUMBER = "20458205"


async def main():
    # Create tables if they do not exist yet.
    Base.metadata.create_all(bind=engine)

    price = await fetch_product_price(PRODUCT_URL)

    with SessionLocal() as db:
        product = db.scalar(
            select(Product).where(
                Product.article_number == ARTICLE_NUMBER
            )
        )

        if product is None:
            product = Product(
                article_number=ARTICLE_NUMBER,
                name="PAX wardrobe frame dark grey 100x58x236",
                url=PRODUCT_URL,
            )

            db.add(product)
            db.flush()

        observation = PriceObservation(
            product_id=product.id,
            price=price,
        )

        db.add(observation)
        db.commit()

        print(
            f"Stored price observation: "
            f"{ARTICLE_NUMBER} = €{price:.2f}"
        )


if __name__ == "__main__":
    asyncio.run(main())