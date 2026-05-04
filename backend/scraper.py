"""
Job scraper — only uses sources confirmed to return real data without auth.

  1. LinkedIn  — SSR public pages, 60 jobs/city, works for all Indian cities
  2. Remotive  — free REST API, remote PM jobs globally
"""
from __future__ import annotations

import hashlib
import logging
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


def _make_external_id(source: str, value: str) -> str:
    return hashlib.md5(f"{source}:{value}".encode()).hexdigest()


def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=(500, 502, 503, 504))
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ─── 1. LinkedIn ───────────────────────────────────────────────────────────────
# Public SSR pages — no auth, no JS needed, ~60 jobs per city.

LINKEDIN_CITIES: dict[str, str] = {
    "Bangalore": "Bangalore%2C+Karnataka%2C+India",
    "Mumbai":    "Mumbai%2C+Maharashtra%2C+India",
    "Delhi":     "Delhi%2C+India",
    "Hyderabad": "Hyderabad%2C+Telangana%2C+India",
    "Pune":      "Pune%2C+Maharashtra%2C+India",
}

# Normalize raw location strings so filters work reliably
_LOCATION_NORM = [
    ("bengaluru", "Bangalore"),
    ("bangalore", "Bangalore"),
    ("bombay",    "Mumbai"),
    ("new delhi", "Delhi"),
    ("ncr",       "Delhi"),
]

def _normalize_location(raw: str) -> str:
    low = raw.lower()
    for pattern, canonical in _LOCATION_NORM:
        if pattern in low:
            return canonical
    return raw.split(",")[0].strip().title()  # take first segment


_PAGES_PER_CITY = 5   # 5 pages × 25 results = 125 per city × 5 cities = 625 jobs

def scrape_linkedin_city(city: str, location_param: str, session: requests.Session, query: str = "Product Manager") -> list[dict]:
    jobs: list[dict] = []
    seen_ids: set = set()

    for page in range(_PAGES_PER_CITY):
        start = page * 25
        url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={query.replace(' ', '+')}"
            f"&location={location_param}"
            f"&start={start}"
            f"&sortBy=DD"
            f"&f_TPR=r2592000"
        )
        try:
            resp = session.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select("div.base-card")
            if not cards:
                break

            for card in cards:
                title_el   = card.select_one("h3.base-search-card__title")
                company_el = card.select_one("h4.base-search-card__subtitle")
                loc_el     = card.select_one("span.job-search-card__location")
                date_el    = card.select_one("time")
                link_el    = card.select_one("a.base-card__full-link")

                if not title_el:
                    continue

                title   = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                job_url = link_el.get("href", "").split("?")[0] if link_el else ""
                ext_id  = _make_external_id("linkedin", job_url or title + company + city)

                if ext_id in seen_ids:
                    continue
                seen_ids.add(ext_id)

                raw_loc = loc_el.get_text(strip=True) if loc_el else city
                jobs.append({
                    "title":       title,
                    "company":     company,
                    "location":    _normalize_location(raw_loc),
                    "source":      "linkedin",
                    "url":         job_url,
                    "description": "",
                    "salary":      "",
                    "experience":  "",
                    "posted_date": date_el.get("datetime", "") if date_el else "",
                    "external_id": ext_id,
                })

            time.sleep(random.uniform(0.6, 1.2))
        except Exception as e:
            logger.error(f"LinkedIn {city} page {page}: {e}")
            break

    logger.info(f"LinkedIn {city}: {len(jobs)} jobs")
    return jobs


def scrape_linkedin_all(query: str = "Product Manager") -> list[dict]:
    all_jobs: list[dict] = []
    session = _make_session()
    for city, location_param in LINKEDIN_CITIES.items():
        all_jobs.extend(scrape_linkedin_city(city, location_param, session, query))
        time.sleep(random.uniform(1, 2))
    return all_jobs


# ─── 2. Remotive ───────────────────────────────────────────────────────────────
# Free REST API — no auth, returns remote PM jobs globally.

def scrape_remotive(query: str = "product manager") -> list[dict]:
    jobs: list[dict] = []
    try:
        resp = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"category": "product", "limit": 50},
            timeout=15,
        )
        resp.raise_for_status()
        for item in resp.json().get("jobs", []):
            title = item.get("title", "")
            if query.lower() not in title.lower():
                continue
            job_url = item.get("url", "")
            jobs.append({
                "title":       title,
                "company":     item.get("company_name", "Unknown"),
                "location":    "Remote",
                "source":      "remotive",
                "url":         job_url,
                "description": BeautifulSoup(item.get("description", "")[:800], "lxml").get_text()[:500],
                "salary":      item.get("salary", ""),
                "experience":  "",
                "posted_date": item.get("publication_date", "")[:10],
                "external_id": _make_external_id("remotive", job_url),
            })
        logger.info(f"Remotive: {len(jobs)} PM remote jobs")
    except Exception as e:
        logger.error(f"Remotive: {e}")
    return jobs


# ─── Master runner ─────────────────────────────────────────────────────────────

def run_all_scrapers(query: str = "Product Manager") -> list[dict]:
    from scraper_playwright import scrape_indeed as pw_indeed, scrape_google_careers

    all_jobs: list[dict] = []
    li_slug = query.lower().replace(" ", "-")

    # LinkedIn runs via HTTP (fast). Indeed + Google Careers use Playwright (headless).
    # All three run in parallel — total wall time ≈ slowest single source (~30s).
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(scrape_linkedin_all, li_slug): "linkedin",
            pool.submit(pw_indeed, query):             "indeed",
            pool.submit(scrape_google_careers, query): "google_careers",
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                chunk = future.result(timeout=180)
                all_jobs.extend(chunk)
                logger.info(f"{name}: {len(chunk)} jobs")
            except Exception as e:
                logger.error(f"{name} worker failed: {e}")

    logger.info(f"Total scraped: {len(all_jobs)}")
    return all_jobs
