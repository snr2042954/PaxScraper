import json
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class IkeaProduct:
    article_number: str
    name: str
    price: float
    url: str


def extract_article_number(url: str) -> str:
    path = urlparse(url).path

    match = re.search(
        r"(\d{8})/?$",
        path,
    )

    if not match:
        raise ValueError(
            "Could not extract IKEA article number "
            f"from URL: {url}"
        )

    return match.group(1)


def normalize_article_number(
    value: str | None,
) -> str | None:
    if not value:
        return None

    digits = re.sub(
        r"\D",
        "",
        str(value),
    )

    if len(digits) == 8:
        return digits

    return None


def iter_json_nodes(value):
    if isinstance(value, dict):
        yield value

        for child in value.values():
            yield from iter_json_nodes(
                child
            )

    elif isinstance(value, list):
        for child in value:
            yield from iter_json_nodes(
                child
            )


def extract_offer_price(
    offers,
) -> float | None:
    if isinstance(offers, dict):
        offers = [offers]

    if not isinstance(offers, list):
        return None

    for offer in offers:
        if not isinstance(offer, dict):
            continue

        price = offer.get("price")

        if isinstance(price, dict):
            price = (
                price.get("value")
                or price.get("price")
            )

        if price is None:
            price_spec = offer.get(
                "priceSpecification"
            )

            if isinstance(
                price_spec,
                dict,
            ):
                price = price_spec.get(
                    "price"
                )

        try:
            if price is not None:
                return float(price)

        except (
            TypeError,
            ValueError,
        ):
            continue

    return None


async def fetch_product(
    url: str,
) -> IkeaProduct:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
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

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    article_number = (
        extract_article_number(url)
    )

    # -----------------------------------------------------
    # First try structured JSON-LD.
    # This now also walks nested @graph structures and
    # combination-product data.
    # -----------------------------------------------------

    product_nodes = []

    for script in soup.find_all(
        "script",
        type="application/ld+json",
    ):
        try:
            data = json.loads(
                script.string or script.get_text()
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ):
            continue

        for node in iter_json_nodes(data):
            node_type = node.get("@type")

            if (
                node_type == "Product"
                or (
                    isinstance(
                        node_type,
                        list,
                    )
                    and "Product"
                    in node_type
                )
            ):
                product_nodes.append(node)

    # Prefer a Product node whose SKU/article matches
    # the URL article number.
    ordered_nodes = sorted(
        product_nodes,
        key=lambda node: (
            normalize_article_number(
                node.get("sku")
                or node.get("productID")
                or node.get("mpn")
            )
            != article_number
        ),
    )

    for node in ordered_nodes:
        name = node.get("name")

        price = extract_offer_price(
            node.get("offers")
        )

        if name and price is not None:
            return IkeaProduct(
                article_number=article_number,
                name=str(name).strip(),
                price=price,
                url=str(response.url),
            )

    # -----------------------------------------------------
    # Fallback for IKEA combination pages.
    # -----------------------------------------------------

    h1 = soup.find("h1")

    name = None

    if h1:
        name = " ".join(
            h1.stripped_strings
        )

    if not name:
        og_title = soup.find(
            "meta",
            attrs={
                "property": "og:title",
            },
        )

        if og_title:
            name = og_title.get(
                "content"
            )

    price = None

    price_selectors = [
        (
            "meta",
            {
                "property":
                "product:price:amount"
            },
        ),
        (
            "meta",
            {
                "itemprop": "price",
            },
        ),
    ]

    for tag_name, attrs in price_selectors:
        tag = soup.find(
            tag_name,
            attrs=attrs,
        )

        if not tag:
            continue

        raw_price = (
            tag.get("content")
            or tag.get("value")
        )

        try:
            if raw_price is not None:
                price = float(
                    str(raw_price)
                    .replace(",", ".")
                )
                break

        except ValueError:
            continue

    if name and price is not None:
        return IkeaProduct(
            article_number=article_number,
            name=name.strip(),
            price=price,
            url=str(response.url),
        )

    raise ValueError(
        "Could not parse IKEA product "
        f"{article_number} from {url}"
    )