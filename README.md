Web Scraper Dashboard

A lightweight, production-ready starter that combines a Tailwind CSS frontend with a FastAPI backend to scrape public websites and return normalized JSON you can explore in a table, filter, and export to CSV.

Frontend: static/index.html (Tailwind via CDN, no Node build needed)

Backend: app.py (FastAPI + Requests + BeautifulSoup + lxml)

Modes: Site-specific scrapers (Books/Quotes) + a universal fallback (JSON‑LD, OpenGraph, and link-based extraction) so any URL returns useful items.

✨ Features

Universal URL support: Accepts any URL; tries domain-specific handlers first, then generic extraction.

Structured data first: Parses JSON‑LD (application/ld+json) for Product/Article/ItemList when available.

Smart fallback: Uses OpenGraph/meta and content links (with price/rating heuristics) when structured data is absent.

Clean UI: Dark mode, inline filtering, quick stats, CSV export, graceful error states.

Same-origin serving: FastAPI serves the frontend, avoiding CORS headaches.

Polite HTTP: Retries, headers, and small delays to avoid hammering targets.

⚠️ Ethics & Terms: Only scrape content you’re allowed to. Respect robots.txt, site Terms of Service, and legal constraints.

🧭 Repository Structure
project/
├─ app.py                 # FastAPI app (API, scrapers, static serving)
├─ static/
│  └─ index.html          # Tailwind UI (no build step required)
├─ requirements.txt       # (optional) dependencies pinning
└─ README.md              # you are here
🚀 Quickstart
Prerequisites

Python 3.10+ (3.11 recommended)

Install & Run
# 1) Create/activate a virtualenv (recommended)
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate


# 2) Install dependencies
pip install fastapi uvicorn requests beautifulsoup4 lxml


# 3) Start the backend (also serves the frontend)
uvicorn app:app --reload --port 8000


# 4) Open the UI
# → http://127.0.0.1:8000
Try it out

In the input box, enter a URL and click Scrape:

https://books.toscrape.com

http://quotes.toscrape.com

https://en.wikipedia.org/wiki/Web_scraping

https://news.ycombinator.com/

🖥️ Frontend (static/index.html)

Tailwind CDN (no build tooling required)

Auto API detection:

If opened via FastAPI: calls same-origin /api/scrape.

If opened as file://: calls http://127.0.0.1:8000/api/scrape.

UI elements:

URL input, Scrape and Use Demo Data buttons

Status badge (shows API base)

Table with inline filter, CSV download, and summary stats

Dark mode toggle

The page expects /api/scrape?url=<target> to return a JSON array of items.

🔌 API Reference
GET /api/scrape?url=<target>

Returns an array of items with a consistent schema, regardless of source.

Query Parameters

url (string, required): Any absolute URL (or host; https:// will be assumed).

Response (200)

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

Errors

400 – invalid or empty URL

502 – cannot scrape target (upstream error or unsupported structure)

500 – unexpected server error

GET /healthz

Simple readiness probe.

🧠 How It Works
Selection strategy

Domain-specific handlers (fast paths)

books.toscrape.com: rich product fields + pagination

quotes.toscrape.com: quote text, author, tags

Generic extractor (fallback for everything else)

Parse JSON‑LD blocks (Product, ItemList, Article, etc.)

Read OpenGraph/meta tags

Build items from content links in <main>, <article>, .content, etc., guessing prices/ratings when present

Data model
interface Item {
  title: string;
  price?: number;       // when detectable
  stock?: number;       // when detectable
  rating?: number;      // when detectable (e.g., 4.5/5)
  product_url?: string; // canonical or link target
  category?: string;    // category/section/host
}
🧪 Testing & Examples
# Health
curl http://127.0.0.1:8000/healthz


# Books (pagination)
curl "http://127.0.0.1:8000/api/scrape?url=https://books.toscrape.com"


# Quotes
curl "http://127.0.0.1:8000/api/scrape?url=http://quotes.toscrape.com"


# Wikipedia article
curl "http://127.0.0.1:8000/api/scrape?url=https://en.wikipedia.org/wiki/Web_scraping"
🐳 Docker (optional)

Create requirements.txt:

fastapi
uvicorn[standard]
requests
beautifulsoup4
lxml

Dockerfile:

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8000
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

Build & run:

docker build -t scraper-dashboard .
docker run --rm -p 8000:8000 scraper-dashboard
🔐 Security, Legal & Performance

Respect robots.txt & ToS: Only scrape where permitted.

Rate limiting: Be gentle; the sample code includes small delays.

PII: Do not collect/store personal data without explicit consent and lawful basis.

Dynamic sites: Some pages render via JS; consider Playwright for those.

🛠️ Troubleshooting

Message: “Could not reach the backend”

Ensure the server is running: uvicorn app:app --reload --port 8000

Open http://127.0.0.1:8000/healthz → should return { "ok": true }

If you previously mounted static at /, your /api routes may have been shadowed. In this repo we serve static at /static and return index.html from /.

CORS errors

When serving frontend from FastAPI (same origin), CORS shouldn’t trigger.

If you host the UI elsewhere, adjust CORSMiddleware to whitelist your origin.

Firewall prompts (Windows/macOS)

Allow Python to accept local connections on first run.

🧭 Roadmap

Optional Playwright integration for JS-heavy SPAs

Per-domain parsers (Amazon/eBay/OpenLibrary/Wikipedia tables)

Configurable rate limits & caching

Export to JSON/Parquet

Minimal test suite

🤝 Contributing

Issues and PRs are welcome! Please:

Open an issue describing the change/bug.

Include clear steps to reproduce or a concise proposal.

Keep code style consistent and add tests where possible.

🙏 Acknowledgments

Books to Scrape & Quotes to Scrape (public demo sites for training/practice)

FastAPI, Requests, BeautifulSoup, lxml, Tailwind CSS

📄 License

This project is licensed under the MIT License. See LICENSE for details.