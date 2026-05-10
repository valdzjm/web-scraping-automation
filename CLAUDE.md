# Scraper Project

This project is for extracting data from websites — scraping pages, crawling entire sites, mapping URL structures, taking screenshots, and pulling structured data. The goal is clean, usable output: markdown content, JSON data, or screenshots saved to `.tmp/`.

## How to Work

**Always use the Firecrawl MCP server first.** You have direct access to it — no Python scripts needed for most tasks. Read [`workflows/firecrawl_reference.md`](workflows/firecrawl_reference.md) to choose the right tool and get parameter syntax.

Only fall back to `tools/scrape_website.py` if the MCP server is unavailable or a task requires custom post-processing.

## What You Can Do

- **Scrape a page** → `firecrawl_scrape` — single URL to markdown, HTML, screenshot, or links
- **Map a site** → `firecrawl_map` — get every URL on a domain without scraping content
- **Crawl a site** → `firecrawl_crawl` + `firecrawl_check_crawl_status` — bulk scrape all pages
- **Search the web** → `firecrawl_search` — find pages + optionally scrape them
- **Extract structured data** → `firecrawl_extract` — schema or prompt-driven JSON extraction
- **Deep research** → `firecrawl_deep_research` — synthesize across many sources into a report
- **Site overview** → `firecrawl_generate_llmstxt` — AI-friendly summary of site structure

## MCP Server

**Server name:** `firecrawl`  
**Reference:** [`workflows/firecrawl_reference.md`](workflows/firecrawl_reference.md) — tool parameters, decision guide, credit costs, and common patterns.

## File Layout

```
tools/          # Python scripts (fallback execution)
workflows/      # Reference docs and SOPs
.tmp/           # All output goes here (disposable, regeneratable)
.env            # FIRECRAWL_API_KEY lives here
```

## Rules

- Save all output to `.tmp/<domain>.<ext>` unless told otherwise
- Never hardcode API keys — they're in `.env`
- Check credit cost before running `firecrawl_extract` or `firecrawl_deep_research` on large sets
- When a crawl job is async, poll `firecrawl_check_crawl_status` every 5–10 seconds until `completed`
