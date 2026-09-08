from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class TrackedProduct:
    url: str
    quantity_needed: int = 1
    target_price: float | None = None


def load_products() -> list[TrackedProduct]:
    config_path = Path("products.yaml")

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return [
        TrackedProduct(
            url=item["url"],
            quantity_needed=item.get("quantity_needed", 1),
            target_price=item.get("target_price"),
        )
        for item in config["products"]
    ]