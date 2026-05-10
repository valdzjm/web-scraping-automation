"""
Scrape a website to markdown using the Firecrawl crawl API.

Usage:
    python tools/scrape_website.py <url> [--limit N] [--output .tmp/output.md]

Firecrawl crawl API crawls all pages under the given URL and returns each
page as clean markdown. Results are saved as a single combined .md file and
a JSON file with per-page metadata.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FIRECRAWL_API_KEY")
BASE_URL = "https://api.firecrawl.dev/v1"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def start_crawl(url: str, limit: int) -> str:
    resp = requests.post(
        f"{BASE_URL}/crawl",
        headers=HEADERS,
        json={
            "url": url,
            "limit": limit,
            "scrapeOptions": {"formats": ["markdown"]},
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Crawl start failed: {data}")
    return data["id"]


def poll_crawl(crawl_id: str, poll_interval: int = 5) -> list[dict]:
    print(f"Crawl ID: {crawl_id} — polling every {poll_interval}s ...")
    while True:
        resp = requests.get(
            f"{BASE_URL}/crawl/{crawl_id}",
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        completed = data.get("completed", 0)
        total = data.get("total", "?")
        print(f"  status={status}  pages={completed}/{total}")

        if status == "completed":
            return data.get("data", [])
        if status in ("failed", "cancelled"):
            raise RuntimeError(f"Crawl ended with status: {status}")

        time.sleep(poll_interval)


def save_results(pages: list[dict], output_md: Path, output_json: Path) -> None:
    output_md.parent.mkdir(parents=True, exist_ok=True)

    sections = []
    for page in pages:
        url = page.get("metadata", {}).get("sourceURL", "unknown")
        title = page.get("metadata", {}).get("title", "")
        md = page.get("markdown", "")
        header = f"# {title}\n\n> Source: {url}\n\n" if title else f"> Source: {url}\n\n"
        sections.append(header + md)

    combined = "\n\n---\n\n".join(sections)
    output_md.write_text(combined, encoding="utf-8")

    slim = [
        {
            "url": p.get("metadata", {}).get("sourceURL"),
            "title": p.get("metadata", {}).get("title"),
            "chars": len(p.get("markdown", "")),
        }
        for p in pages
    ]
    output_json.write_text(json.dumps(slim, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape a website to markdown via Firecrawl.")
    parser.add_argument("url", help="Root URL to crawl")
    parser.add_argument("--limit", type=int, default=50, help="Max pages to crawl (default 50)")
    parser.add_argument("--output", default=None, help="Output .md path (default: .tmp/<domain>.md)")
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: FIRECRAWL_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    domain = args.url.replace("https://", "").replace("http://", "").strip("/").split("/")[0]
    out_md = Path(args.output) if args.output else Path(f".tmp/{domain}.md")
    out_json = out_md.with_suffix(".json")

    print(f"Starting crawl of {args.url} (limit={args.limit}) ...")
    crawl_id = start_crawl(args.url, args.limit)
    pages = poll_crawl(crawl_id)

    print(f"\nCrawled {len(pages)} pages. Saving ...")
    save_results(pages, out_md, out_json)

    total_chars = sum(len(p.get("markdown", "")) for p in pages)
    print(f"\nDone.")
    print(f"  Markdown : {out_md}  ({total_chars:,} chars)")
    print(f"  Metadata : {out_json}")
    print(f"  Pages    : {len(pages)}")


if __name__ == "__main__":
    main()
