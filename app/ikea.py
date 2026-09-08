import json
import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup


@dataclass
class IkeaProduct:
    article_number: str
    name: str
    price: float
    url: str


def extract_article_number(url: str) -> str:
    match = re.search(r"(\d{8})/?$", url)

    if not match:
        raise ValueError(
            f"Could not extract IKEA article number from URL: {url}"
        )

    return match.group(1)


async def fetch_product(url: str) -> IkeaProduct:
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

    article_number = extract_article_number(url)

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

            return IkeaProduct(
                article_number=article_number,
                name=name,
                price=float(price),
                url=url,
            )

    raise ValueError(f"Could not extract product data from {url}")