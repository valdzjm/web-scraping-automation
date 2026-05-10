"""
Extract structured job listings from OnlineJobs.ph using Firecrawl /extract API.

Usage:
    python tools/extract_jobs.py
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

# API key from settings (fallback to .env)
API_KEY = "fc-7070e7e7c3bf4862a77dd61cbdf2297e"
BASE_URL = "https://api.firecrawl.dev/v1"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

URLS = [
    "https://www.onlinejobs.ph/jobseekers/jobsearch?jobkeyword=AI+Automation&skill_tags=&gig=on&partTime=on&fullTime=on",
    "https://www.onlinejobs.ph/jobseekers/jobsearch/2?jobkeyword=AI+Automation&skill_tags=&gig=on&partTime=on&fullTime=on",
]

PROMPT = (
    "Extract all job listings shown on this page. For each job listing extract: "
    "job title, employment type (Part Time / Full Time / Gig / Any), date posted, "
    "salary or rate (as raw text exactly as shown), a short description snippet "
    "(first 1-2 sentences), the full job detail URL, and the skill tags."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "jobs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "job_title": {"type": "string"},
                    "employment_type": {"type": "string"},
                    "date_posted": {"type": "string"},
                    "salary": {"type": "string"},
                    "description_snippet": {"type": "string"},
                    "job_url": {"type": "string"},
                    "skills": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    },
}


def start_extract() -> str:
    payload = {
        "urls": URLS,
        "prompt": PROMPT,
        "schema": SCHEMA,
    }
    resp = requests.post(
        f"{BASE_URL}/extract",
        headers=HEADERS,
        json=payload,
        timeout=60,
    )
    print(f"HTTP {resp.status_code}")
    if resp.status_code != 200:
        print("Response body:", resp.text)
        resp.raise_for_status()
    data = resp.json()
    print("Response keys:", list(data.keys()))
    return data


def poll_extract(job_id: str, poll_interval: int = 5) -> dict:
    print(f"Extract job ID: {job_id} — polling every {poll_interval}s ...")
    for attempt in range(60):  # max ~5 minutes
        resp = requests.get(
            f"{BASE_URL}/extract/{job_id}",
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        print(f"  attempt={attempt+1}  status={status}")

        if status == "completed":
            return data
        if status in ("failed", "cancelled"):
            raise RuntimeError(f"Extract job ended with status: {status}\n{data}")

        time.sleep(poll_interval)

    raise TimeoutError("Extract job did not complete within timeout")


def main():
    output_path = Path("d:/Tech/Claude Code/AIS 7 Day Challenge/Scraper/.tmp/jobs_page1_2.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Starting Firecrawl extract job...")
    result = start_extract()

    # Handle both sync (immediate data) and async (job ID) responses
    if "data" in result:
        # Synchronous response — data returned immediately
        print("Synchronous response received.")
        final = result["data"]
    elif "id" in result:
        # Async response — poll for completion
        job_id = result["id"]
        completed = poll_extract(job_id)
        final = completed.get("data", completed)
    else:
        print("Unexpected response structure:", json.dumps(result, indent=2))
        sys.exit(1)

    # Save raw result
    output_path.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved to: {output_path}")

    # Report stats
    jobs = []
    if isinstance(final, dict):
        jobs = final.get("jobs", [])
    elif isinstance(final, list):
        # May be list of per-URL results
        for item in final:
            if isinstance(item, dict) and "jobs" in item:
                jobs.extend(item["jobs"])

    print(f"\nTotal jobs extracted: {len(jobs)}")
    if jobs:
        print("\nFirst 3 job entries (sample):")
        print(json.dumps(jobs[:3], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
