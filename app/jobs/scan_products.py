import asyncio

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import Product
from app.services.price_checker import check_product_price


async def main():
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        products = db.scalars(
            select(Product).order_by(Product.article_number)
        ).all()

        if not products:
            print("No products are currently being tracked.")
            return

        print(f"Scanning {len(products)} product(s)...\n")

        for product in products:
            try:
                result = await check_product_price(db, product)

                print(f"{product.name}")
                print(f"Article: {result.article_number}")

                if result.previous_price is None:
                    print(
                        f"Baseline price stored: "
                        f"€{result.current_price:.2f}"
                    )

                elif not result.changed:
                    print(
                        f"Price unchanged: "
                        f"€{result.current_price:.2f}"
                    )

                else:
                    difference = (
                        result.current_price
                        - result.previous_price
                    )

                    percentage = (
                        difference / result.previous_price
                    ) * 100

                    print(
                        f"Previous: €{result.previous_price:.2f}"
                    )
                    print(
                        f"Current:  €{result.current_price:.2f}"
                    )
                    print(
                        f"Change:   €{difference:+.2f} "
                        f"({percentage:+.1f}%)"
                    )

                    if result.dropped:
                        print("PRICE DROP")
                    else:
                        print("Price increased.")

                print()

            except Exception as exc:
                print(f"{product.name}")
                print(f"ERROR: {exc}\n")


if __name__ == "__main__":
    asyncio.run(main())