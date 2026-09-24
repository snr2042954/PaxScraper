from dataclasses import dataclass

import httpx


SECOND_HAND_API = (
    "https://web-api.ikea.com/"
    "circular/circular-asis/offers/grouped/search"
)

STORE_METADATA_URL = (
    "https://www.ikea.com/nl/nl/"
    "meta-data/informera/stores-suggested.json"
)


@dataclass
class SecondHandOffer:
    offer_uuid: str
    article_number: str
    store_id: str

    title: str
    description: str

    original_price: float
    price: float

    condition_code: str | None
    condition_title: str | None
    condition_description: str | None

    reason_discount: str | None
    additional_info: str | None

    image_url: str | None


def slugify_store_name(name: str) -> str:
    return (
        name.lower()
        .replace("ikea ", "")
        .replace(" - ", " ")
        .replace("-", " ")
        .strip()
        .replace(" ", "-")
    )


async def fetch_store_mapping() -> dict[str, str]:
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
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        response = await client.get(
            STORE_METADATA_URL
        )

        response.raise_for_status()

        data = response.json()

    mapping: dict[str, str] = {}

    for store in data:
        classification = (
            store.get("buClassification", {})
            .get("code")
        )

        # Only keep full IKEA stores.
        if classification != "STORE":
            continue

        store_id = str(store["id"])

        display_name = (
            store.get("displayName")
            or store.get("displayNameAlternate")
            or store.get("name")
            or ""
        )

        slug = slugify_store_name(display_name)

        mapping[slug] = store_id

    return mapping


async def resolve_store_ids(
    store_names: list[str],
) -> dict[str, str]:
    mapping = await fetch_store_mapping()

    resolved: dict[str, str] = {}
    unresolved: list[str] = []

    for store_name in store_names:
        key = slugify_store_name(store_name)

        if key not in mapping:
            unresolved.append(store_name)
            continue

        resolved[store_name] = mapping[key]

    if unresolved:
        print(
            "WARNING: Could not resolve IKEA store IDs for: "
            + ", ".join(unresolved)
        )

    return resolved


async def fetch_second_hand_store(
    store_id: str,
) -> list[SecondHandOffer]:

    offers: list[SecondHandOffer] = []

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
        timeout=30.0,
    ) as client:

        page = 0

        while True:
            response = await client.get(
                SECOND_HAND_API,
                params={
                    "languageCode": "nl",
                    "size": 32,
                    "storeIds": store_id,
                    "page": page,
                },
            )

            response.raise_for_status()

            data = response.json()

            for item in data.get("content", []):
                article_numbers = item.get(
                    "articleNumbers",
                    [],
                )

                for raw_offer in item.get(
                    "offers",
                    [],
                ):
                    for article_number in article_numbers:
                        offers.append(
                            SecondHandOffer(
                                offer_uuid=str(
                                    raw_offer["offerUuid"]
                                ),
                                article_number=article_number,
                                store_id=str(
                                    item["storeId"]
                                ),
                                title=item.get(
                                    "title",
                                    "",
                                ),
                                description=item.get(
                                    "description",
                                    "",
                                ),
                                original_price=float(
                                    item["originalPrice"]
                                ),
                                price=float(
                                    raw_offer["price"]
                                ),
                                condition_code=raw_offer.get(
                                    "productConditionCode"
                                ),
                                condition_title=raw_offer.get(
                                    "productConditionTitle"
                                ),
                                condition_description=raw_offer.get(
                                    "productConditionDescription"
                                ),
                                reason_discount=raw_offer.get(
                                    "reasonDiscount"
                                ),
                                additional_info=raw_offer.get(
                                    "additionalInfo"
                                ),
                                image_url=item.get(
                                    "heroImage"
                                ),
                            )
                        )

            total_pages = data.get(
                "totalPages",
                1,
            )

            page += 1

            if page >= total_pages:
                break

    return offers