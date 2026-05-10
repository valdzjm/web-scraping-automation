"""
Scrape and parse AI Automation job listings from OnlineJobs.ph.
Scrapes all result pages via Firecrawl, parses markdown, deduplicates,
and saves structured output to .tmp/ as both JSON and CSV.

Usage:
    python tools/parse_jobs.py
"""

import csv
import json
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

API_KEY = os.environ["FIRECRAWL_API_KEY"]
BASE_URL = "https://api.firecrawl.dev/v1"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

SEARCH_BASE = "https://www.onlinejobs.ph/jobseekers/jobsearch"
QUERY = "jobkeyword=AI+Automation&skill_tags=&gig=on&partTime=on&fullTime=on"
PAGE_SIZE = 30
TOTAL_PAGES = 10  # 299 jobs / 30 per page = 10 pages

EMPLOYMENT_TYPES = ["Full Time", "Part Time", "Gig", "Any"]

OUTPUT_DIR = Path(__file__).parent.parent / ".tmp"
OUTPUT_JSON = OUTPUT_DIR / "onlinejobs_ai_automation.json"
OUTPUT_CSV = OUTPUT_DIR / "onlinejobs_ai_automation.csv"


def page_url(page: int) -> str:
    if page == 1:
        return f"{SEARCH_BASE}?{QUERY}"
    offset = (page - 1) * PAGE_SIZE
    return f"{SEARCH_BASE}/{offset}?{QUERY}"


def scrape_page(url: str) -> str:
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": False,
        "waitFor": 2000,
    }
    resp = requests.post(f"{BASE_URL}/scrape", headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["data"]["markdown"]


def extract_employment_type(title: str) -> tuple[str, str]:
    for emp_type in EMPLOYMENT_TYPES:
        if title.endswith(f" {emp_type}"):
            return title[: -(len(emp_type) + 1)].strip(), emp_type
    return title.strip(), "Unknown"


def parse_skill_links(text: str) -> list[str]:
    return re.findall(
        r'\[([^\]]+)\]\(https://www\.onlinejobs\.ph/jobseekers/search/c/[^\)]+\)',
        text,
    )


def parse_jobs_from_markdown(markdown: str) -> list[dict]:
    jobs = []

    job_header_pattern = re.compile(
        r'\[\*\*(.+?)\*\*\\\\\n_Posted on ([0-9\-: ]+)_\\\\\n(.*?)\]'
        r'\((https://www\.onlinejobs\.ph/jobseekers/job/[^\)]+)\)',
        re.DOTALL,
    )
    desc_pattern = re.compile(
        r'\[(.+?)\]\(https://www\.onlinejobs\.ph/jobseekers/job/[^\)]+\)\s+\[See More\]',
        re.DOTALL,
    )

    headers = list(job_header_pattern.finditer(markdown))

    for i, match in enumerate(headers):
        raw_title = match.group(1).strip()
        date_posted = match.group(2).strip()
        salary = match.group(3).strip()
        job_url = match.group(4).strip()

        raw_title = raw_title.replace(r"\|", "|")
        job_title, employment_type = extract_employment_type(raw_title)

        start = match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(markdown)
        block = markdown[start:end]

        description_snippet = ""
        desc_match = desc_pattern.search(block)
        if desc_match:
            raw = desc_match.group(1).strip()
            raw = re.sub(r'\\\\\n\\\\\n', ' ', raw)
            raw = re.sub(r'\\\\\n', ' ', raw)
            raw = re.sub(r'\s+', ' ', raw).strip()
            sentences = re.split(r'(?<=[.!?])\s+', raw)
            description_snippet = " ".join(sentences[:2])[:300]

        skills = parse_skill_links(block)

        jobs.append({
            "job_title": job_title,
            "employment_type": employment_type,
            "date_posted": date_posted,
            "salary": salary,
            "description_snippet": description_snippet,
            "job_url": job_url,
            "skills": "; ".join(skills),
        })

    return jobs


def save_csv(jobs: list[dict], path: Path) -> None:
    if not jobs:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
        writer.writeheader()
        writer.writerows(jobs)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_jobs: list[dict] = []
    seen_urls: set[str] = set()
    page_counts: dict[str, int] = {}

    for page in range(1, TOTAL_PAGES + 1):
        url = page_url(page)
        print(f"\nScraping page {page}/{TOTAL_PAGES}: {url}")
        try:
            markdown = scrape_page(url)
        except Exception as e:
            print(f"  ERROR: {e} — skipping page {page}")
            continue

        jobs = parse_jobs_from_markdown(markdown)
        new_jobs = [j for j in jobs if j["job_url"] not in seen_urls]
        for j in new_jobs:
            seen_urls.add(j["job_url"])

        page_counts[f"page_{page}"] = len(new_jobs)
        all_jobs.extend(new_jobs)
        print(f"  Parsed: {len(jobs)} | New (deduped): {len(new_jobs)} | Running total: {len(all_jobs)}")

        if page < TOTAL_PAGES:
            time.sleep(1)

    # Save JSON
    result = {
        "meta": {
            "total_jobs": len(all_jobs),
            "page_counts": page_counts,
            "pages_scraped": TOTAL_PAGES,
        },
        "jobs": all_jobs,
    }
    OUTPUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nJSON saved -> {OUTPUT_JSON}")

    # Save CSV
    save_csv(all_jobs, OUTPUT_CSV)
    print(f"CSV saved  -> {OUTPUT_CSV}")

    print(f"\n--- SUMMARY ---")
    for page_key, count in page_counts.items():
        print(f"  {page_key}: {count} new jobs")
    print(f"  Total unique jobs: {len(all_jobs)}")


if __name__ == "__main__":
    main()
