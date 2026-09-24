from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class TrackedProduct:
    url: str
    quantity_needed: int = 1
    target_price: float | None = None


@dataclass
class SecondHandConfig:
    enabled: bool
    scan_interval_hours: int
    min_discount_percent: float
    stores: dict[str, str]


@dataclass
class AppConfig:
    products: list[TrackedProduct]
    second_hand: SecondHandConfig


def load_config() -> AppConfig:
    path = Path("products.yaml")

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    products = [
        TrackedProduct(
            url=item["url"],
            quantity_needed=item.get("quantity_needed", 1),
            target_price=item.get("target_price"),
        )
        for item in data["products"]
    ]

    second_hand_data = data.get("second_hand", {})

    second_hand = SecondHandConfig(
        enabled=second_hand_data.get("enabled", False),
        scan_interval_hours=second_hand_data.get(
            "scan_interval_hours",
            1,
        ),
        min_discount_percent=second_hand_data.get(
            "min_discount_percent",
            10,
        ),
        stores=second_hand_data.get(
            "stores",
            [],
        ),
    )

    return AppConfig(
        products=products,
        second_hand=second_hand,
    )


def load_products() -> list[TrackedProduct]:
    return load_config().products