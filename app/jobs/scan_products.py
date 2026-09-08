import asyncio

from app.config import load_products
from app.db import Base, SessionLocal, engine
from app.ikea import fetch_product
from app.services.price_checker import check_product_price


async def main():
    Base.metadata.create_all(bind=engine)

    tracked_products = load_products()

    print(f"Scanning {len(tracked_products)} product(s)...\n")

    with SessionLocal() as db:

        for tracked in tracked_products:
            try:
                product = await fetch_product(tracked.url)

                result = check_product_price(
                    db,
                    product,
                )

                print(product.name)
                print(f"Article: {product.article_number}")
                print(f"Needed:  {tracked.quantity_needed}")

                if tracked.target_price is not None:
                    print(
                        f"Target:  €{tracked.target_price:.2f}"
                    )

                if result.previous_price is None:
                    print(
                        f"Baseline stored: "
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
                        difference
                        / result.previous_price
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

                if (
                    tracked.target_price is not None
                    and product.price <= tracked.target_price
                ):
                    print("TARGET PRICE REACHED")

                print()

            except Exception as exc:
                print(f"ERROR checking {tracked.url}")
                print(f"{exc}\n")


if __name__ == "__main__":
    asyncio.run(main())