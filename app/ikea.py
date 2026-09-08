import json
import re

import httpx
from bs4 import BeautifulSoup


PRODUCT_URL = (
    "https://www.ikea.com/nl/en/p/"
    "pax-wardrobe-frame-dark-grey-20458205/"
)


async def fetch_product_price(url: str) -> float:
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

    # First try structured JSON-LD embedded in the page.
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

            offers = entry.get("offers")

            if isinstance(offers, dict) and offers.get("price"):
                return float(offers["price"])

    raise ValueError("Could not find product price")


if __name__ == "__main__":
    import asyncio

    price = asyncio.run(fetch_product_price(PRODUCT_URL))
    print(f"Current IKEA price: €{price:.2f}")