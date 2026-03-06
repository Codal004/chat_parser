"""
HTML parser for PDB (PersonalityDatabase.com) web chat exports.

Expects the page saved via File > Save Page As... (Webpage, Complete or HTML Only).

Structure observed in PDB's HTML:
  <ul class="message-list">
    <li class="time-item">March 03</li>
    <li class="message-item is-multi-first is-self" data-message-key="...">
      <span class="text-container">
        <div style="padding: ...">
          <div class="quote">          <!-- optional: reply-to -->
            <label class="username">otheruser</label>
            <label class="text">quoted text</label>
          </div>
          <label class="text">actual message</label>  <!-- may be absent for media -->
          <div class="web">...</div>                  <!-- optional: link preview -->
        </div>
      </span>
    </li>
    ...
  </ul>

Sender detection:
  - 'is-self' in classes → sender = 'me'
  - otherwise            → sender = 'other'

Timestamps:
  - Only date separators exist (e.g. "March 03").
  - No per-message time is available, so we track the last seen date
    and assign it to all messages that follow.
"""
from __future__ import annotations

import sys
from typing import Optional

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 not installed. Run: pip install beautifulsoup4 lxml", file=sys.stderr)
    sys.exit(1)


def _extract_text(item) -> str:
    """
    Extract only the direct message text, ignoring the quote block.
    Returns empty string for pure media messages.
    """
    container = item.find(class_="text-container")
    if not container:
        return ""

    # Clone container and remove the quote sub-tree so its text isn't included
    # We work on a copy to avoid mutating the parse tree
    import copy
    container_copy = copy.copy(container)
    for q in container_copy.find_all(class_="quote"):
        q.decompose()
    # Also remove the tools div
    for t in container_copy.find_all(class_="tools"):
        t.decompose()

    # Primary text label
    text_label = container_copy.find(class_="text")
    if text_label:
        return text_label.get_text("\n", strip=True)

    # Web link preview: "title — domain"
    web_div = container_copy.find(class_="web")
    if web_div:
        title = web_div.find(class_="title")
        desc = web_div.find(class_="description")
        parts = []
        if title:
            parts.append(title.get_text(strip=True))
        if desc:
            parts.append(desc.get_text(strip=True))
        return " — ".join(parts) if parts else "[Link]"

    return ""


def _extract_quote(item) -> Optional[str]:
    """
    If the message is a reply, return a formatted '> Name: text' string.
    """
    quote_div = item.find(class_="quote")
    if not quote_div:
        return None
    username = quote_div.find(class_="username")
    qtext = quote_div.find(class_="text")
    name = username.get_text(strip=True) if username else "?"
    text = qtext.get_text(strip=True) if qtext else ""
    return f"> {name}: {text}"


def _has_media(item) -> bool:
    """True if the message contains an image/media that isn't a UI logo."""
    for img in item.find_all("img"):
        classes = img.get("class", [])
        src = img.get("src", "")
        if "logo" not in classes and "header_logo" not in src:
            return True
    return False


def extract_reactions(filepath: str) -> dict[str, list[str]]:
    """
    Return a dict mapping normalised message body text → list of reaction emojis.
    Used to enrich HAR-parsed messages with reactions visible in the saved HTML.
    """
    with open(filepath, encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f, "lxml")

    result: dict[str, list[str]] = {}
    msg_list = soup.find(class_="message-list")
    if not msg_list:
        return result

    for li in msg_list.find_all("li", recursive=False):
        if "message-item" not in (li.get("class") or []):
            continue

        emojis = [el.get_text(strip=True) for el in li.find_all(class_="reaction-icon")]
        if not emojis:
            continue

        body = _extract_text(li).strip()
        if not body:
            continue

        key = " ".join(body.lower().split())
        result[key] = emojis

    return result


def parse_html(filepath: str) -> list[dict]:
    """
    Parse a PDB chat HTML export and return a list of message dicts:
      {
        'sender':    'me' | 'other',
        'timestamp': str | None,   # date only, e.g. 'March 03'
        'text':      str,
      }
    """
    with open(filepath, encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f, "lxml")

    msg_list = soup.find(class_="message-list")
    if not msg_list:
        print("WARNING: Could not find <ul class='message-list'>. Is this a PDB chat page?", file=sys.stderr)
        return []

    messages = []
    current_date: Optional[str] = None

    for li in msg_list.find_all("li", recursive=False):
        classes = li.get("class", [])

        # Date separator
        if "time-item" in classes:
            current_date = li.get_text(strip=True)
            continue

        if "message-item" not in classes:
            continue

        sender = "me" if "is-self" in classes else "other"

        # Build the message text
        quote = _extract_quote(li)
        body = _extract_text(li)
        has_media = _has_media(li)

        parts = []
        if quote:
            parts.append(quote)
        if body:
            parts.append(body)
        elif has_media and not body:
            parts.append("[Image]")

        text = "\n".join(parts)

        if not text:
            continue  # skip empty / purely structural elements

        messages.append({
            "sender": sender,
            "timestamp": current_date,
            "text": text,
        })

    print(f"Parsed {len(messages)} messages from HTML.", file=sys.stderr)
    return messages
