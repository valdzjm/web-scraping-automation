# Firecrawl MCP Reference

**MCP Server:** `firecrawl` (via `firecrawl-mcp` npx package)  
**API Key:** Set in `~/.claude/settings.json` as `FIRECRAWL_API_KEY`  
**Direct API fallback:** `tools/scrape_website.py` (crawl) and `.tmp/test_firecrawl.py` (single scrape)

---

## Tool Overview

| Tool | Use When | Speed |
|---|---|---|
| `firecrawl_scrape` | Single page → clean content | Fast |
| `firecrawl_map` | Discover all URLs on a domain | Fast |
| `firecrawl_crawl` | Multi-page site → bulk markdown | Slow (async) |
| `firecrawl_check_crawl_status` | Poll a running crawl job | Instant |
| `firecrawl_cancel_crawl` | Stop a crawl early | Instant |
| `firecrawl_search` | Web search + optional scrape results | Medium |
| `firecrawl_extract` | Pull structured data via schema/prompt | Medium |
| `firecrawl_deep_research` | Comprehensive research across many sources | Slow |
| `firecrawl_generate_llmstxt` | Get AI-friendly site summary | Medium |

---

## `firecrawl_scrape`

Scrapes a single URL and returns content in the requested format(s).

```
url: string (required)
formats: ["markdown", "html", "rawHtml", "screenshot", "links"]  # default: markdown
onlyMainContent: true     # strips nav, footer, ads (default: true)
includeTags: ["article"]  # only include these HTML tags
excludeTags: ["nav", "footer", "aside"]
waitFor: 2000             # ms to wait before scraping (for JS-heavy pages)
timeout: 30000            # ms total timeout
actions:                  # browser automation before scrape
  - type: "click", selector: "#load-more"
  - type: "scroll", direction: "down", amount: 3
  - type: "wait", milliseconds: 1000
  - type: "screenshot"
```

**Best for:** Blog posts, landing pages, docs pages, any single-URL content extraction.  
**Returns:** Markdown text, metadata (title, description, sourceURL, statusCode).

---

## `firecrawl_map`

Returns all URLs found on a domain without scraping content.

```
url: string (required)          # root URL to map
search: "pricing"               # filter URLs containing this term
ignoreSitemap: false            # use sitemap.xml when available (default: false)
includeSubdomains: false        # also map docs.example.com, etc.
limit: 100                      # max URLs to return (default: 100, max: 5000)
```

**Best for:** Site audits, finding specific pages before crawling, understanding site structure.  
**Returns:** Array of URL strings.

---

## `firecrawl_crawl`

Starts an async job that crawls all pages under a URL and scrapes each one.

```
url: string (required)
excludePaths: ["/blog/*", "/tag/*"]   # skip these path patterns
includePaths: ["/docs/*"]             # only crawl these paths
maxDepth: 3                           # link depth from root (default: 2)
limit: 50                             # max pages (default: 10)
ignoreSitemap: false
scrapeOptions:
  formats: ["markdown"]
  onlyMainContent: true
  excludeTags: ["nav", "footer"]
```

**Returns immediately:** `{ id: "crawl-job-id", success: true }`  
**Then poll:** `firecrawl_check_crawl_status` with that ID until `status: "completed"`.

**Best for:** Full site docs ingestion, competitor research, building knowledge bases.

---

## `firecrawl_check_crawl_status`

Polls the status of a running crawl job.

```
id: "crawl-job-id" (required)
```

**Returns:**
```json
{
  "status": "completed",   // scraping | completed | failed | cancelled
  "completed": 42,
  "total": 50,
  "data": [{ "markdown": "...", "metadata": { "sourceURL": "...", "title": "..." } }]
}
```

**Pattern:** Poll every 5–10 seconds until `status === "completed"`.

---

## `firecrawl_cancel_crawl`

Cancels a crawl job before it finishes.

```
id: "crawl-job-id" (required)
```

---

## `firecrawl_search`

Web search that can optionally scrape the result pages.

```
query: "n8n workflow automation tutorial" (required)
limit: 5                          # number of results (default: 5)
lang: "en"                        # language code
country: "us"                     # country code
scrapeOptions:
  formats: ["markdown"]
  onlyMainContent: true
```

**Without scrapeOptions:** Returns URLs + snippets only (fast).  
**With scrapeOptions:** Returns full page content for each result (slower, uses more credits).  
**Best for:** Research, finding documentation, competitive analysis.

---

## `firecrawl_extract`

Uses an LLM to extract structured data from one or more pages according to a schema or prompt.

```
urls: ["https://example.com/pricing", "https://example.com/about"]
prompt: "Extract company name, pricing tiers, and contact email"
schema:                           # optional JSON schema for structured output
  type: object
  properties:
    company_name: { type: string }
    pricing_tiers: { type: array, items: { type: object } }
    contact_email: { type: string }
enableWebSearch: false            # use web search to supplement missing data
ignoreSitemap: false
```

**Best for:** Lead enrichment, price comparison, extracting contact info, structured data collection.  
**Returns:** Structured JSON matching your schema.

---

## `firecrawl_deep_research`

Conducts multi-step research on a topic by searching, reading, and synthesizing across many sources.

```
query: "What are the best practices for n8n error handling?" (required)
maxDepth: 3                   # research iteration depth (default: 3)
timeLimit: 120                # seconds (default: 60)
maxUrls: 20                   # max pages to visit (default: 10)
```

**Best for:** Complex research questions, market research, technical deep-dives.  
**Returns:** Comprehensive markdown report with sources.  
**Note:** Slow and credit-intensive — use only when breadth and synthesis matter.

---

## `firecrawl_generate_llmstxt`

Generates an LLMs.txt file for a website (AI-friendly summary of site structure and content).

```
url: "https://docs.example.com" (required)
maxUrls: 10                   # pages to include (default: 10)
showFullText: false           # include full page text vs summaries
```

**Best for:** Quickly understanding what a site covers before deciding how to scrape it.  
**Returns:** LLMs.txt formatted content (structured site overview).

---

## Decision Guide

```
Need content from 1 page?
  └→ firecrawl_scrape

Need to find which pages exist?
  └→ firecrawl_map

Need content from all/many pages?
  └→ firecrawl_crawl  →  poll firecrawl_check_crawl_status

Need to search the web?
  └→ firecrawl_search (add scrapeOptions to also get page content)

Need structured/typed data extracted?
  └→ firecrawl_extract

Need comprehensive research on a topic?
  └→ firecrawl_deep_research

Need a high-level overview of a site?
  └→ firecrawl_generate_llmstxt
```

---

## Common Patterns

**JS-rendered pages (SPAs):** Add `waitFor: 2000` to `firecrawl_scrape`.

**Clean article content only:** Set `onlyMainContent: true` and `excludeTags: ["nav","footer","aside","header"]`.

**Limit crawl to one section:** Use `includePaths: ["/docs/*"]` in `firecrawl_crawl`.

**Get links only (no content):** Use `formats: ["links"]` in `firecrawl_scrape`.

**Bulk structured extraction:** `firecrawl_map` → filter URLs → `firecrawl_extract` with schema.

---

## Credit Cost (approximate)

| Tool | Credits |
|---|---|
| `firecrawl_scrape` | 1 per page |
| `firecrawl_map` | 1 per job |
| `firecrawl_crawl` | 1 per page crawled |
| `firecrawl_search` | 1 per search + 1 per scraped result |
| `firecrawl_extract` | 5 per URL |
| `firecrawl_deep_research` | High (varies by depth/URLs) |
| `firecrawl_generate_llmstxt` | 1–2 per job |

Check usage at: https://www.firecrawl.dev/dashboard
