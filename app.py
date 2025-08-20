# app.py
from typing import List, Optional, Any, Dict
from urllib.parse import urljoin, urlparse
import time, os, json, re

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ---------------- Models ----------------
class Item(BaseModel):
    title: str
    price: Optional[float] = None
    stock: Optional[int] = None
    rating: Optional[float] = None
    product_url: Optional[str] = None
    category: Optional[str] = None

# ---------------- App ----------------
app = FastAPI(title="Universal Scraper API", version="1.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/healthz")
def health():
    return {"ok": True}

# ---------------- HTTP helpers ----------------
def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; EduScraper/2.0; +https://example.edu)",
        "Accept-Language": "en-US,en;q=0.9",
    })
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

def abs_url(base: str, href: Optional[str]) -> Optional[str]:
    if not href: return None
    try:
        return urljoin(base, href)
    except Exception:
        return None

# ---------------- Site-specific: BooksToScrape ----------------
RATING_MAP = {"One":1, "Two":2, "Three":3, "Four":4, "Five":5}

def extract_category_books(soup: BeautifulSoup) -> Optional[str]:
    li_nodes = soup.select("ul.breadcrumb li")
    if li_nodes:
        last = li_nodes[-1].get_text(strip=True)
        return None if last.lower() in {"home", "books"} else last
    return None

def parse_book_card(card: BeautifulSoup, page_url: str, category: Optional[str]) -> Item:
    a = card.select_one("h3 a")
    title = a.get("title", a.get_text(strip=True)).strip()
    product_url = abs_url(page_url, a.get("href"))

    # Price
    price = None
    p = card.select_one(".price_color")
    if p:
        try: price = float(p.get_text(strip=True).replace("£", "").replace(",", ""))
        except: pass

    # Stock
    stock = None
    av = card.select_one(".availability")
    if av:
        digits = re.sub(r"[^\d]", "", av.get_text(strip=True))
        stock = int(digits) if digits else None

    # Rating
    rating = None
    rc = card.select_one(".star-rating")
    if rc:
        for c in rc.get("class", []):
            if c in RATING_MAP: rating = float(RATING_MAP[c]); break

    return Item(title=title, price=price, stock=stock, rating=rating,
                product_url=product_url, category=category)

def parse_books_list(html: str, page_url: str):
    soup = BeautifulSoup(html, "lxml")
    category = extract_category_books(soup)
    items = [parse_book_card(c, page_url, category) for c in soup.select("article.product_pod")]
    next_rel = soup.select_one("li.next a")
    next_url = abs_url(page_url, next_rel.get("href")) if next_rel else None
    return items, next_url

def scrape_books_to_scrape(url: str, delay=0.25) -> List[Item]:
    parsed = urlparse(url if "://" in url else "https://" + url)
    if "books.toscrape.com" not in parsed.netloc:
        raise HTTPException(status_code=400, detail="Not books.toscrape.com")
    base = "https://books.toscrape.com/"
    if parsed.path in ("", "/", "/index.html"):
        url = urljoin(base, "catalogue/page-1.html")
    session = make_session()
    out, seen = [], set()
    while url and url not in seen:
        seen.add(url)
        r = session.get(url, timeout=20); r.raise_for_status()
        items, url = parse_books_list(r.text, r.url)
        out.extend(items); time.sleep(delay)
    return out

# ---------------- Site-specific: QuotesToScrape ----------------
def scrape_quotes_to_scrape(url: str, delay=0.2) -> List[Item]:
    parsed = urlparse(url if "://" in url else "http://" + url)  # quotes is http
    if "quotes.toscrape.com" not in parsed.netloc:
        raise HTTPException(status_code=400, detail="Not quotes.toscrape.com")
    session, out, seen = make_session(), [], set()
    url = parsed.geturl()
    while url and url not in seen:
        seen.add(url)
        r = session.get(url, timeout=15); r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        for q in soup.select(".quote"):
            text = q.select_one(".text").get_text(strip=True)
            author = q.select_one(".author").get_text(strip=True)
            tags = [t.get_text(strip=True) for t in q.select(".tags .tag")]
            out.append(Item(
                title=text,
                category=f"Author: {author}" + (f" | Tags: {', '.join(tags)}" if tags else ""),
                product_url=None
            ))
        next_rel = soup.select_one("li.next a")
        url = abs_url(r.url, next_rel.get("href")) if next_rel else None
        time.sleep(delay)
    return out

# ---------------- Generic Extractor (ANY site) ----------------
PRICE_RE = re.compile(r"(?<!\d)(?:[$€£]|USD|EUR|GBP)\s?\d[\d,]*(?:\.\d{1,2})?|\d[\d,]*\s?(?:USD|EUR|GBP)(?!\w)")
RATING_TEXT_RE = re.compile(r"(\d+(?:\.\d+)?)[/ ]*5")
STAR_RE = re.compile(r"★+|☆+")

def try_parse_float(x: Any) -> Optional[float]:
    try:
        if x is None: return None
        if isinstance(x, (int, float)): return float(x)
        return float(str(x).replace(",", ""))
    except: return None

def jsonld_blocks(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    blocks = []
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
            if isinstance(data, list): blocks.extend(data)
            elif isinstance(data, dict): blocks.append(data)
        except Exception:
            continue
    return blocks

def extract_items_from_jsonld(blocks: List[Dict[str, Any]], base_url: str) -> List[Item]:
    items: List[Item] = []
    def norm_url(u): return abs_url(base_url, u) if isinstance(u, str) else None

    for b in blocks:
        t = b.get("@type") or b.get("type")
        # ItemList → walk elements
        if t in ("ItemList",) and "itemListElement" in b:
            for el in b["itemListElement"]:
                if isinstance(el, dict):
                    it = el.get("item") or el.get("url") or el
                    name = (it.get("name") if isinstance(it, dict) else None) or (isinstance(it, str) and it) or "Item"
                    url = norm_url(it.get("url")) if isinstance(it, dict) else norm_url(it)
                    items.append(Item(title=str(name), product_url=url))
        # Product
        if t in ("Product",):
            name = b.get("name") or "Product"
            offers = b.get("offers") or {}
            if isinstance(offers, list): offers = offers[0] if offers else {}
            price = try_parse_float(offers.get("price"))
            availability = str(offers.get("availability", "")).lower()
            stock = None
            if "instock" in availability: stock = 1
            if "outofstock" in availability: stock = 0
            rating = None
            agg = b.get("aggregateRating") or {}
            rating = try_parse_float(agg.get("ratingValue"))
            url = norm_url(b.get("url"))
            cat = b.get("category") or (b.get("brand", {}).get("name") if isinstance(b.get("brand"), dict) else None)
            items.append(Item(title=str(name), price=price, stock=stock, rating=rating, product_url=url, category=cat))
        # Article-like
        if t in ("Article","NewsArticle","BlogPosting"):
            name = b.get("headline") or b.get("name") or "Article"
            url = norm_url(b.get("url"))
            items.append(Item(title=str(name), product_url=url, category=b.get("articleSection") or "Article"))

    return items

def extract_items_from_links(soup: BeautifulSoup, base_url: str, limit=40) -> List[Item]:
    # Focus on likely content areas
    candidates = soup.select("main a, article a, .content a, .post a, .card a, .product a, .entry a, .listing a")
    if not candidates:
        candidates = soup.select("a")
    out: List[Item] = []
    seen = set()
    for a in candidates:
        text = a.get_text(" ", strip=True)
        href = abs_url(base_url, a.get("href"))
        if not href or not text or len(text) < 2: continue
        key = (text.lower(), href)
        if key in seen: continue
        seen.add(key)
        # Guess price in text
        price = None
        m = PRICE_RE.search(text)
        if m:
            price_num = re.sub(r"[^\d.]", "", m.group())
            price = try_parse_float(price_num)
        # Guess rating from 4.2/5 or stars
        rating = None
        mr = RATING_TEXT_RE.search(text)
        if mr:
            rating = try_parse_float(mr.group(1))
        else:
            stars = STAR_RE.search(text)
            if stars:
                rating = len(stars.group().replace("☆",""))
        out.append(Item(title=text[:200], product_url=href, price=price, rating=rating, category=urlparse(href).netloc))
        if len(out) >= limit: break
    return out

def extract_items_generic(url: str) -> List[Item]:
    session = make_session()
    resp = session.get(url if "://" in url else "https://" + url, timeout=25)
    resp.raise_for_status()
    base = resp.url  # follow redirects
    soup = BeautifulSoup(resp.text, "lxml")

    # 1) JSON-LD first
    blocks = jsonld_blocks(soup)
    items = extract_items_from_jsonld(blocks, base)
    if items:
        return items

    # 2) Try OpenGraph/meta → single item fallback
    og_title = soup.select_one('meta[property="og:title"]')
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
        og_url = soup.select_one('meta[property="og:url"]')
        og_type = soup.select_one('meta[property="og:type"]')
        items.append(Item(
            title=title,
            product_url=og_url.get("content") if og_url else base,
            category=(og_type.get("content") if og_type else urlparse(base).netloc)
        ))
        # plus links as extra items for richness
        items.extend(extract_items_from_links(soup, base, limit=30))
        return items

    # 3) As last resort: build items from links in main content
    items = extract_items_from_links(soup, base, limit=40)
    if items:
        return items

    # 4) Absolute last: page <title> as a single item
    page_title = soup.title.get_text(strip=True) if soup.title else urlparse(base).netloc
    return [Item(title=page_title, product_url=base, category=urlparse(base).netloc)]

# ---------------- Router: choose best handler ----------------
def scrape_universal(target_url: str) -> List[Item]:
    if not target_url or not target_url.strip():
        raise HTTPException(status_code=400, detail="Empty URL.")
    # Normalize protocol if missing (try https first)
    parsed = urlparse(target_url if "://" in target_url else "https://" + target_url)
    url = parsed.geturl()

    # 1) Site-specific fast paths
    host = parsed.netloc.lower()
    try_handlers = []
    if "books.toscrape.com" in host: try_handlers.append(lambda: scrape_books_to_scrape(url))
    if "quotes.toscrape.com" in host: try_handlers.append(lambda: scrape_quotes_to_scrape(url))

    # 2) Generic handler at end
    try_handlers.append(lambda: extract_items_generic(url))

    last_err = None
    for h in try_handlers:
        try:
            data = h()
            if data and isinstance(data, list):
                return data
        except HTTPException as e:
            # If the handler says "not supported", try next
            last_err = e
            continue
        except Exception as e:
            last_err = e
            continue

    # If everything failed hard, bubble a clear error
    raise HTTPException(status_code=502, detail=f"Could not scrape the target: {last_err}")

# ---------------- API ----------------
@app.get("/api/scrape", response_model=List[Item])
def api_scrape(url: str = Query(..., description="Target URL (any site)")):
    try:
        return scrape_universal(url)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scrape failed: {e}")
