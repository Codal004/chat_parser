"""
Formats parsed messages into WhatsApp-style .txt output.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional


def format_timestamp(ts: Optional[str]) -> str:
    """Try to normalise a timestamp string into 'YYYY-MM-DD, HH:MM'."""
    if not ts:
        return "unknown date"

    ts = ts.strip()

    # Already looks like a date we can work with
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M",
        "%B %d, %Y %H:%M",
        "%b %d, %Y %H:%M",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(ts, fmt)
            return dt.strftime("%Y-%m-%d, %H:%M")
        except ValueError:
            continue

    # Return as-is for relative timestamps like "just now", "2 hours ago"
    return ts


def write_export(messages: list[dict], output_path: str, me: str, other: str) -> None:
    """
    Write messages to a WhatsApp-style text file.

    Each message dict must have:
      - 'sender': 'me' | 'other' | raw name string
      - 'timestamp': str or None
      - 'text': str
    """
    lines = []
    for msg in messages:
        raw_sender = msg.get("sender", "")
        if raw_sender == "me":
            sender_label = me
        elif raw_sender == "other":
            sender_label = other
        else:
            # Raw name already provided
            sender_label = raw_sender or "Unknown"

        ts = format_timestamp(msg.get("timestamp"))
        text = msg.get("text", "").strip()
        if not text:
            text = "[Media]"

        # Handle multi-line messages: indent continuation lines
        text_lines = text.splitlines()
        first_line = f"[{ts}] {sender_label}: {text_lines[0]}"
        rest_lines = [f"  {l}" for l in text_lines[1:]]
        lines.append(first_line)
        lines.extend(rest_lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        if lines:
            f.write("\n")

    # Summary stats
    dates = [m.get("timestamp") for m in messages if m.get("timestamp")]
    me_count = sum(1 for m in messages if m.get("sender") == "me")
    other_count = sum(1 for m in messages if m.get("sender") == "other")

    print(f"\n=== Export complete ===")
    print(f"Output file : {output_path}")
    print(f"Total msgs  : {len(messages)}")
    print(f"  {me} (you) : {me_count}")
    print(f"  {other}    : {other_count}")
    if dates:
        print(f"Date range  : {dates[0]}  →  {dates[-1]}")
