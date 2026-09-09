import os

import httpx
from dotenv import load_dotenv


load_dotenv()


PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")


async def send_pushover_notification(
    title: str,
    message: str,
    url: str | None = None,
) -> None:
    if not PUSHOVER_USER_KEY or not PUSHOVER_API_TOKEN:
        raise RuntimeError(
            "PUSHOVER_USER_KEY or PUSHOVER_API_TOKEN is not configured"
        )

    payload = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "title": title,
        "message": message,
    }

    if url:
        payload["url"] = url
        payload["url_title"] = "View on IKEA"

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "https://api.pushover.net/1/messages.json",
            data=payload,
        )

        response.raise_for_status()