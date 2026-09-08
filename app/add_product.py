import asyncio
import json
import re

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import PriceObservation, Product


def extract_article_number(url: str) -> str:
    match = re.search(r"-(\d{8})/?$", url)

    if not match:
        raise ValueError(
            "Could not extract an 8-digit IKEA article number from the URL."
        )

    return match.group(1)


async def fetch_product_details(url: str) -> tuple[str, float]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=20.0,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue

        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            continue

        entries = data if isinstance(data, list) else [data]

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            if entry.get("@type") != "Product":
                continue

            name = entry.get("name")
            offers = entry.get("offers")

            if not name or not isinstance(offers, dict):
                continue

            price = offers.get("price")

            if price is None:
                continue

            return name, float(price)

    raise ValueError("Could not extract product details from IKEA page.")


async def main():
    Base.metadata.create_all(bind=engine)

    url = input("IKEA product URL: ").strip()

    article_number = extract_article_number(url)

    print("\nFetching IKEA product...")

    name, current_price = await fetch_product_details(url)

    with SessionLocal() as db:
        existing_product = db.scalar(
            select(Product).where(
                Product.article_number == article_number
            )
        )

        if existing_product:
            print("\nAlready tracked:")
            print(f"{existing_product.name}")
            print(f"Article: {article_number}")
            return

        product = Product(
            article_number=article_number,
            name=name,
            url=url,
        )

        db.add(product)
        db.flush()

        db.add(
            PriceObservation(
                product_id=product.id,
                price=current_price,
            )
        )

        db.commit()

    print("\nProduct added.")
    print(f"Name:    {name}")
    print(f"Article: {article_number}")
    print(f"Price:   €{current_price:.2f}")


if __name__ == "__main__":
    asyncio.run(main())