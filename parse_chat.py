#!/usr/bin/env python3
"""
parse_chat.py — PDB chat export parser

Usage:
  # From HAR file (Network > Save all as HAR):
  python parse_chat.py --har archive.har --me "YourName" --other "TheirName"

  # From saved HTML (File > Save Page As):
  python parse_chat.py --html chat.html --me "YourName" --other "TheirName"

  # From DevTools JSON response:
  python parse_chat.py --json messages.json --me "YourName" --other "TheirName"

  # Output to a specific file (default: chat_export.txt):
  python parse_chat.py --har archive.har --out my_chat.txt
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Convert a PDB web chat export to WhatsApp-style .txt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--har", metavar="FILE", help="HAR archive (Network tab > Save all as HAR)")
    source.add_argument("--html", metavar="FILE", help="Saved HTML file (File > Save Page As)")
    source.add_argument("--json", metavar="FILE", help="DevTools JSON response file")

    parser.add_argument("--me", default="You", metavar="NAME", help="Your display name (default: You)")
    parser.add_argument("--other", default="Them", metavar="NAME", help="Other person's display name (default: Them)")
    parser.add_argument("--out", default="chat_export.txt", metavar="FILE", help="Output file (default: chat_export.txt)")

    args = parser.parse_args()

    if args.har:
        from har_parser import parse_har
        messages = parse_har(args.har)
    elif args.html:
        from html_parser import parse_html
        messages = parse_html(args.html)
    else:
        from json_parser import parse_json
        messages = parse_json(args.json)

    if not messages:
        print("No messages found. Check the input file and try again.", file=sys.stderr)
        sys.exit(1)

    from formatter import write_export
    write_export(messages, args.out, me=args.me, other=args.other)


if __name__ == "__main__":
    main()
