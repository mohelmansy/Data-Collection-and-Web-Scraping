# Web Scraper Dashboard

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)]()
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-UI-06B6D4?logo=tailwindcss&logoColor=white)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)]()

A lightweight, production-ready starter that pairs a **Tailwind CSS** frontend with a **FastAPI** backend to scrape public web pages and return normalized JSON you can browse, filter, and export to CSV. Includes domain-specific scrapers (Books/Quotes) and a universal fallback that extracts JSON-LD/OpenGraph/meta (so *any* URL returns useful items).

> **Ethics & Terms** — Only scrape content you are permitted to access. Respect robots.txt, site Terms of Service, and applicable laws.

---

## Table of Contents

- [Features](#features)  
- [Architecture](#architecture)  
- [Repository Structure](#repository-structure)  
- [Quickstart](#quickstart)  
- [Frontend](#frontend)  
- [API Reference](#api-reference)  
- [Testing & Examples](#testing--examples)  
- [Docker](#docker)  
- [Troubleshooting](#troubleshooting)  
- [Security & Legal](#security--legal)  
- [Roadmap](#roadmap)  
- [Contributing](#contributing)  
- [License](#license)

---

## Features

- **Universal URL support** — Accepts any URL; runs domain-specific handlers first (Books/Quotes), then a robust generic extractor.
- **Structured data first** — Parses **JSON-LD** (`application/ld+json`) for `Product`, `ItemList`, `Article`, etc.
- **Smart fallbacks** — Uses **OpenGraph/meta** and content links (with price/rating heuristics) when structured data is absent.
- **Clean UI** — Dark mode, inline filtering, quick stats, CSV export, and clear status feedback.
- **Same-origin serving** — FastAPI serves the frontend, avoiding CORS headaches.
- **Polite HTTP** — Retries, headers, and small delays to avoid hammering targets.

---

## Architecture

```
Browser (Tailwind UI)
    │  enters URL, clicks "Scrape"
    ▼
FastAPI (/api/scrape?url=...)
    ├─ books.toscrape.com handler (pagination, price/stock/rating)
    ├─ quotes.toscrape.com handler (quote, author, tags)
    └─ generic extractor
         ├─ JSON-LD (Product/Article/ItemList)
         ├─ OpenGraph/meta
         └─ link-based extraction (main/article/content areas)
    ▼
Normalized JSON
    └─ rendered in table + stats + CSV export
```

**Data model**
```ts
interface Item {
  title: string;
  price?: number;
  stock?: number;
  rating?: number;
  product_url?: string;
  category?: string;
}
```

---

## Repository Structure

```
project/
├─ app.py                 # FastAPI app (API, scrapers, static serving)
├─ static/
│  └─ index.html          # Tailwind UI (no Node build step required)
├─ requirements.txt       # Dependencies
└─ README.md              # This file
```

---

## Quickstart

### Prerequisites
- Python **3.10+** (3.11 recommended)

### Install & Run
```bash
# 1) (Optional) Use a virtual environment
python -m venv .venv
# Windows:
# .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2) Install dependencies
pip install -r requirements.txt
# or
pip install fastapi uvicorn[standard] requests beautifulsoup4 lxml

# 3) Start backend (also serves the frontend)
uvicorn app:app --reload --port 8000

# 4) Open the UI
# http://127.0.0.1:8000
```

### Try it out
Paste any of these into the input, then click **Scrape**:
- `https://books.toscrape.com`
- `http://quotes.toscrape.com`
- `https://en.wikipedia.org/wiki/Web_scraping`
- `https://news.ycombinator.com/`

---

## Frontend

**File:** `static/index.html`  
- Tailwind CDN (no build tooling)  
- **Auto API detection**:
  - Served via FastAPI → calls same-origin `/api/scrape`.
  - Opened as `file://` → calls `http://127.0.0.1:8000/api/scrape`.  
- UI:
  - URL input, **Scrape** & **Use Demo Data**
  - Status badge (current API base)
  - Table with filter, **CSV download**, and summary stats
  - Dark mode toggle

> The page expects: `/api/scrape?url=<target>` → JSON array of `Item`.

---

## API Reference

### `GET /api/scrape?url=<target>`
Returns an array of normalized items.

**Query Parameters**
- `url` *(required)* — Any absolute URL (or host; `https://` assumed if missing)

**200 Response (example)**
```json
[
  {
    "title": "A Light in the Attic",
    "price": 51.77,
    "stock": 22,
    "rating": 3,
    "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
    "category": "Poetry"
  }
]
```

**Error Codes**
- `400` — invalid/empty URL
- `502` — target could not be scraped (unsupported upstream structure or failure)
- `500` — unexpected server error

### `GET /healthz`
Simple readiness probe. Responds with:
```json
{ "ok": true }
```

---

## Testing & Examples

```bash
# Health
curl http://127.0.0.1:8000/healthz

# Books (pagination)
curl "http://127.0.0.1:8000/api/scrape?url=https://books.toscrape.com"

# Quotes
curl "http://127.0.0.1:8000/api/scrape?url=http://quotes.toscrape.com"

# Wikipedia article
curl "http://127.0.0.1:8000/api/scrape?url=https://en.wikipedia.org/wiki/Web_scraping"
```

---

## Docker

**requirements.txt**
```
fastapi
uvicorn[standard]
requests
beautifulsoup4
lxml
```

**Dockerfile**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8000
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build & Run**
```bash
docker build -t scraper-dashboard .
docker run --rm -p 8000:8000 scraper-dashboard
```

---

## Troubleshooting

- **“Could not reach the backend”**
  - Ensure server is running: `uvicorn app:app --reload --port 8000`
  - Check `http://127.0.0.1:8000/healthz` → should return `{ "ok": true }`
  - If you previously mounted static at `/`, it may shadow `/api/*`. In this setup, static is served at `/static`, and `/` returns `index.html`.
- **CORS**
  - When serving the UI from FastAPI (same origin), CORS isn’t an issue.
  - If hosting elsewhere, update `CORSMiddleware` to allow your origin.
- **Firewall prompts (Windows/macOS)**
  - Allow Python to accept local connections on first run.

---

## Security & Legal

- Respect **robots.txt** and **Terms of Service**
- Rate-limit requests and avoid heavy loads
- Avoid collecting **PII** without lawful basis
- For JS-heavy SPAs, consider **Playwright** (optional extension)

---

## Roadmap

- Optional Playwright integration for dynamic sites
- Domain profiles (Amazon/eBay/OpenLibrary/Wikipedia tables)
- Configurable rate limits & caching
- Export to JSON/Parquet
- Test suite

---

## Contributing

Contributions are welcome:
1. Open an issue describing the change/bug.
2. Provide clear reproduction steps or a concise proposal.
3. Match code style and add tests where reasonable.

---

## License

This project is released under the **MIT License**. See `LICENSE` for details.
