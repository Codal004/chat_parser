"""
Extracts chat messages from a HAR file captured on personality-database.com.

The site uses Stream.io for messaging. The HAR contains many paginated
POST /channels/messaging/.../query responses, each with a 'messages' array.
"""
from __future__ import annotations

import base64
import json


def parse_har(har_path: str, my_user_id: str | None = None) -> list[dict]:
    """
    Parse a HAR file and return messages sorted by timestamp.

    my_user_id: Stream.io numeric user ID (string). If None, it is
                auto-detected from the first query URL (?user_id=...).
    """
    with open(har_path, encoding="utf-8") as f:
        har = json.load(f)

    entries = har["log"]["entries"]

    # Auto-detect my user_id from a query URL if not provided
    if my_user_id is None:
        for e in entries:
            url = e["request"]["url"]
            if "channels/messaging" in url and "/query" in url:
                for part in url.split("?", 1)[-1].split("&"):
                    if part.startswith("user_id="):
                        my_user_id = part.split("=", 1)[1]
                        break
            if my_user_id:
                break

    seen_ids: set[str] = set()
    messages: list[dict] = []

    for e in entries:
        url = e["request"]["url"]
        if "channels/messaging" not in url or "/query" not in url:
            continue
        if e["response"]["status"] not in (200, 201):
            continue

        content = e["response"]["content"]
        text = content.get("text", "")
        if not text:
            continue
        if content.get("encoding") == "base64":
            text = base64.b64decode(text).decode("utf-8")

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue

        for msg in data.get("messages", []):
            if msg.get("type") != "regular":
                continue
            msg_id = msg.get("id")
            if msg_id in seen_ids:
                continue
            seen_ids.add(msg_id)

            sender_id = msg.get("user", {}).get("id", "")
            sender = "me" if sender_id == my_user_id else "other"

            messages.append(
                {
                    "sender": sender,
                    "timestamp": msg.get("created_at"),
                    "text": msg.get("text", "").strip(),
                }
            )

    messages.sort(key=lambda m: m["timestamp"] or "")
    return messages
