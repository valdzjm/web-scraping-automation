"""
Debug: scrape the OnlineJobs.ph search page to see what content Firecrawl can see.
"""

import json
import os
import requests
from pathlib import Path

API_KEY = "fc-7070e7e7c3bf4862a77dd61cbdf2297e"
BASE_URL = "https://api.firecrawl.dev/v1"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

URL = "https://www.onlinejobs.ph/jobseekers/jobsearch?jobkeyword=AI+Automation&skill_tags=&gig=on&partTime=on&fullTime=on"

payload = {
    "url": URL,
    "formats": ["markdown", "links"],
    "onlyMainContent": False,
    "waitFor": 3000,
}

resp = requests.post(f"{BASE_URL}/scrape", headers=HEADERS, json=payload, timeout=60)
print(f"HTTP {resp.status_code}")
data = resp.json()

out = Path("d:/Tech/Claude Code/AIS 7 Day Challenge/Scraper/.tmp/debug_scrape.json")
out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

# Print first 3000 chars of markdown
md = data.get("data", {}).get("markdown", "")
print(f"\nMarkdown length: {len(md)} chars")
print("\n--- FIRST 3000 CHARS ---")
print(md[:3000])
print("\n--- LINKS SAMPLE ---")
links = data.get("data", {}).get("links", [])
print(f"Total links: {len(links)}")
for l in links[:20]:
    print(" ", l)
