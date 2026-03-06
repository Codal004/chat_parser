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
    current_date: Optional[str] = None

    for msg in messages:
        raw_sender = msg.get("sender", "")
        if raw_sender == "me":
            sender_label = me
        elif raw_sender == "other":
            sender_label = other
        else:
            sender_label = raw_sender or "Unknown"

        raw_ts = msg.get("timestamp")
        ts = format_timestamp(raw_ts) if raw_ts else None

        # Determine what to use as the "date" portion for deduplication.
        # For date-only stamps (no time component), ts == the date string itself.
        # For full datetime stamps, extract just the date part (before the comma).
        date_part = ts.split(",")[0].strip() if ts else None

        # Emit a date header only when the date changes
        if date_part and date_part != current_date:
            if lines:
                lines.append("")  # blank line before new section
            lines.append(f"--- {date_part} ---")
            current_date = date_part

        text = msg.get("text", "").strip()
        if not text:
            text = "[Media]"

        # Include time only when it's available (full datetime, not date-only)
        has_time = ts and "," in ts
        prefix = f"[{ts.split(', ')[1]}] {sender_label}: " if has_time else f"{sender_label}: "

        # Handle multi-line messages: indent continuation lines
        text_lines = text.splitlines()
        lines.append(f"{prefix}{text_lines[0]}")
        lines.extend(f"  {l}" for l in text_lines[1:])

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
