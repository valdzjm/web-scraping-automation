"""
Scrape and parse AI Automation job listings from OnlineJobs.ph.
Scrapes paginated results via Firecrawl, parses markdown, deduplicates,
and saves structured output to .tmp/ as both JSON and CSV.

Usage:
    python tools/parse_jobs.py                        # all jobs
    python tools/parse_jobs.py --from 2026-05-09 --to 2026-05-13   # date-filtered
"""

import argparse
import csv
import json
import os
import re
import time
from datetime import date, datetime
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
MAX_PAGES = 10

EMPLOYMENT_TYPES = ["Full Time", "Part Time", "Gig", "Any"]

OUTPUT_DIR = Path(__file__).parent.parent / ".tmp"


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


def job_date(job: dict) -> date:
    return datetime.strptime(job["date_posted"][:10], "%Y-%m-%d").date()


def save_csv(jobs: list[dict], path: Path) -> None:
    if not jobs:
        print("  No jobs to save.")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
        writer.writeheader()
        writer.writerows(jobs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="date_from", help="Start date YYYY-MM-DD (inclusive)")
    parser.add_argument("--to", dest="date_to", help="End date YYYY-MM-DD (inclusive)")
    args = parser.parse_args()

    date_from = datetime.strptime(args.date_from, "%Y-%m-%d").date() if args.date_from else None
    date_to = datetime.strptime(args.date_to, "%Y-%m-%d").date() if args.date_to else None

    if date_from or date_to:
        label = f"{args.date_from or 'start'}_to_{args.date_to or 'end'}"
        output_json = OUTPUT_DIR / f"onlinejobs_{label}.json"
        output_csv = OUTPUT_DIR / f"onlinejobs_{label}.csv"
        print(f"Date filter: {date_from} -> {date_to}")
    else:
        output_json = OUTPUT_DIR / "onlinejobs_ai_automation.json"
        output_csv = OUTPUT_DIR / "onlinejobs_ai_automation.csv"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_jobs: list[dict] = []
    seen_urls: set[str] = set()
    page_counts: dict[str, int] = {}

    for page in range(1, MAX_PAGES + 1):
        url = page_url(page)
        print(f"\nScraping page {page}/{MAX_PAGES}: {url}")
        try:
            markdown = scrape_page(url)
        except Exception as e:
            print(f"  ERROR: {e} — skipping page {page}")
            continue

        jobs = parse_jobs_from_markdown(markdown)
        new_jobs = [j for j in jobs if j["job_url"] not in seen_urls]
        for j in new_jobs:
            seen_urls.add(j["job_url"])

        # Apply date filter
        if date_from or date_to:
            filtered = []
            for j in new_jobs:
                d = job_date(j)
                if date_from and d < date_from:
                    continue
                if date_to and d > date_to:
                    continue
                filtered.append(j)
            new_jobs = filtered

        page_counts[f"page_{page}"] = len(new_jobs)
        all_jobs.extend(new_jobs)
        print(f"  Parsed: {len(jobs)} | In range: {len(new_jobs)} | Running total: {len(all_jobs)}")

        # Stop early if every job on this page is already older than date_from
        if date_from and jobs:
            newest_on_page = max(job_date(j) for j in jobs)
            if newest_on_page < date_from:
                print(f"  All jobs on this page are before {date_from} — stopping early.")
                break

        if page < MAX_PAGES:
            time.sleep(1)

    # Save JSON
    result = {
        "meta": {
            "total_jobs": len(all_jobs),
            "page_counts": page_counts,
            "date_filter": {"from": str(date_from), "to": str(date_to)},
        },
        "jobs": all_jobs,
    }
    output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nJSON saved -> {output_json}")

    save_csv(all_jobs, output_csv)
    print(f"CSV saved  -> {output_csv}")

    print(f"\n--- SUMMARY ---")
    for page_key, count in page_counts.items():
        print(f"  {page_key}: {count} jobs in range")
    print(f"  Total: {len(all_jobs)} jobs")


if __name__ == "__main__":
    main()
