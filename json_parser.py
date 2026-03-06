"""
JSON parser for PDB chat API responses captured via browser DevTools.

How to capture:
  1. Open PDB chat in Chrome/Firefox
  2. Open DevTools → Network tab → refresh the page
  3. Filter by Fetch/XHR, find a request with 'message' or 'chat' in the URL
  4. Right-click the request → Copy → Copy Response
  5. Paste into a .json file and pass it with --json

Tries common API response shapes and field names automatically.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Optional


# Field name candidates in order of preference
_TEXT_FIELDS = ["content", "text", "body", "message", "msg"]
_TS_FIELDS = ["created_at", "timestamp", "sent_at", "date", "time", "created"]
_SENDER_FIELDS = ["sender_id", "from_user_id", "user_id", "author_id"]
_IS_MINE_FIELDS = ["is_mine", "is_self", "mine", "self", "is_sender"]
_SENDER_OBJ_FIELDS = ["sender", "from_user", "author", "user"]


def _get(obj: dict, *keys: str) -> Any:
    """Try multiple field names on a dict, return the first match."""
    for k in keys:
        if k in obj:
            return obj[k]
    return None


def _find_messages(data: Any) -> Optional[list]:
    """Walk common response shapes to find the messages array."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Try common wrapper keys
        for key in ["messages", "data", "items", "results", "chat", "conversation"]:
            val = data.get(key)
            if isinstance(val, list):
                return val
            # One level deeper: data.conversation.messages
            if isinstance(val, dict):
                for sub_key in ["messages", "data", "items"]:
                    sub = val.get(sub_key)
                    if isinstance(sub, list):
                        return sub
    return None


def _determine_sender(msg: dict, my_id: Any) -> str:
    """
    Return 'me' or 'other' for a message dict.
    Uses is_mine boolean if present, otherwise compares sender_id to my_id.
    """
    # Boolean flag — most reliable
    for field in _IS_MINE_FIELDS:
        val = msg.get(field)
        if val is not None:
            return "me" if val else "other"

    # Sender object with nested id
    sender_obj = _get(msg, *_SENDER_OBJ_FIELDS)
    if isinstance(sender_obj, dict):
        sender_id = _get(sender_obj, "id", "user_id", "uid")
        if sender_id is not None and my_id is not None:
            return "me" if sender_id == my_id else "other"

    # Top-level sender id
    sender_id = _get(msg, *_SENDER_FIELDS)
    if sender_id is not None and my_id is not None:
        return "me" if sender_id == my_id else "other"

    return "unknown"


def _infer_my_id(messages: list[dict]) -> Any:
    """
    We can't know for certain which sender_id is 'me', but we can make a
    reasonable guess: look for an is_mine=True message and grab its sender_id.
    """
    for msg in messages:
        for field in _IS_MINE_FIELDS:
            if msg.get(field):
                sender_obj = _get(msg, *_SENDER_OBJ_FIELDS)
                if isinstance(sender_obj, dict):
                    return _get(sender_obj, "id", "user_id", "uid")
                return _get(msg, *_SENDER_FIELDS)
    return None


def parse_json(filepath: str) -> list[dict]:
    """
    Parse a DevTools-captured JSON response and return message dicts:
      {
        'sender':    'me' | 'other' | 'unknown',
        'timestamp': str | None,
        'text':      str,
      }
    """
    with open(filepath, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON — {e}", file=sys.stderr)
            sys.exit(1)

    messages = _find_messages(data)
    if messages is None:
        print(
            "ERROR: Could not find a messages array in the JSON.\n"
            "Looked for keys: messages, data, items, results, chat, conversation\n"
            "Please inspect the JSON and use --json-path to specify the path (e.g. 'data.messages').",
            file=sys.stderr,
        )
        sys.exit(1)

    if not messages:
        print("WARNING: Found messages array but it is empty.", file=sys.stderr)
        return []

    # Detect field names from first message
    first = messages[0]
    text_field = next((f for f in _TEXT_FIELDS if f in first), None)
    ts_field = next((f for f in _TS_FIELDS if f in first), None)

    print(f"Detected fields — text: {text_field!r}, timestamp: {ts_field!r}", file=sys.stderr)

    my_id = _infer_my_id(messages)

    result = []
    for msg in messages:
        text = msg.get(text_field, "") if text_field else ""
        if not isinstance(text, str):
            text = str(text) if text else ""

        ts = msg.get(ts_field, "") if ts_field else None
        if not isinstance(ts, str):
            ts = str(ts) if ts else None

        sender = _determine_sender(msg, my_id)

        result.append({
            "sender": sender,
            "timestamp": ts,
            "text": text.strip(),
        })

    unknown = sum(1 for m in result if m["sender"] == "unknown")
    if unknown:
        print(
            f"WARNING: {unknown} messages have unknown sender.\n"
            "Add --me-id <your_user_id> to resolve them.",
            file=sys.stderr,
        )

    print(f"Parsed {len(result)} messages from JSON.", file=sys.stderr)
    return result
