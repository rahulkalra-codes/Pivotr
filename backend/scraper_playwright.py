"""
Playwright-based scrapers for JS-rendered job sites.
Runs headless Chromium — handles React/Vue SPAs that BeautifulSoup cannot.

Platforms:
  1. Naukri.com       — India's largest job board
  2. Indeed India     — in.indeed.com
  3. Google Careers   — careers.google.com (catches jobs like the one you linked)
  4. Foundit          — foundit.in (Monster India)
"""
from __future__ import annotations

import hashlib
import logging
import time
import random
from typing import Optional

from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)


def _ext_id(source: str, value: str) -> str:
    return hashlib.md5(f"{source}:{value}".encode()).hexdigest()


def _new_browser(playwright):
    return playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
        ],
    )


def _stealth_context(browser: Browser):
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="en-US",
        timezone_id="Asia/Kolkata",
        java_script_enabled=True,
    )
    # Hide webdriver flag
    ctx.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return ctx


# ─── 1. Naukri ────────────────────────────────────────────────────────────────

_NAUKRI_LOCATIONS = ["bangalore", "mumbai", "delhi", "hyderabad", "pune"]

_LOCATION_NORM = {
    "bengaluru": "Bangalore", "bangalore": "Bangalore",
    "mumbai": "Mumbai", "bombay": "Mumbai",
    "delhi": "Delhi", "new delhi": "Delhi", "ncr": "Delhi",
    "hyderabad": "Hyderabad", "pune": "Pune",
}

def _norm_loc(raw: str) -> str:
    low = raw.lower()
    for k, v in _LOCATION_NORM.items():
        if k in low:
            return v
    return raw.split(",")[0].strip().title()


def _scrape_naukri_page(page: Page, query: str, location: str) -> list[dict]:
    jobs: list[dict] = []
    slug_q = query.lower().replace(" ", "-")
    slug_l = location.lower().replace(" ", "-")
    url = f"https://www.naukri.com/{slug_q}-jobs-in-{slug_l}"

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Wait for job cards to appear
        page.wait_for_selector("article.jobTuple, div.srp-jobtuple-wrapper", timeout=15000)
        time.sleep(random.uniform(1, 2))

        cards = page.query_selector_all("article.jobTuple, div.srp-jobtuple-wrapper")
        logger.info(f"Naukri {location}: {len(cards)} raw cards")

        for card in cards[:30]:
            title_el   = card.query_selector("a.title, a.jobTitle")
            company_el = card.query_selector("a.subTitle, span.companyName, a.companyName")
            loc_el     = card.query_selector("li.location span, span.locWdth, span.location")
            exp_el     = card.query_selector("li.experience span, span.expwdth")
            salary_el  = card.query_selector("li.salary span, span.sal")
            date_el    = card.query_selector("span.date, span.fleft.postedDate")

            if not title_el:
                continue

            title   = title_el.inner_text().strip()
            job_url = title_el.get_attribute("href") or ""
            company = company_el.inner_text().strip() if company_el else "Unknown"
            raw_loc = loc_el.inner_text().strip() if loc_el else location

            jobs.append({
                "title":       title,
                "company":     company,
                "location":    _norm_loc(raw_loc),
                "source":      "naukri",
                "url":         job_url if job_url.startswith("http") else f"https://www.naukri.com{job_url}",
                "description": "",
                "salary":      salary_el.inner_text().strip() if salary_el else "",
                "experience":  exp_el.inner_text().strip() if exp_el else "",
                "posted_date": date_el.inner_text().strip() if date_el else "",
                "external_id": _ext_id("naukri", job_url or title + company),
            })
    except PWTimeout:
        logger.warning(f"Naukri {location}: page timeout")
    except Exception as e:
        logger.error(f"Naukri {location}: {e}")

    return jobs


def scrape_naukri(query: str = "Product Manager") -> list[dict]:
    all_jobs: list[dict] = []
    with sync_playwright() as pw:
        browser = _new_browser(pw)
        ctx = _stealth_context(browser)
        page = ctx.new_page()
        for loc in _NAUKRI_LOCATIONS:
            all_jobs.extend(_scrape_naukri_page(page, query, loc))
            time.sleep(random.uniform(1.5, 2.5))
        browser.close()
    logger.info(f"Naukri total: {len(all_jobs)} jobs")
    return all_jobs


# ─── 2. Indeed India ──────────────────────────────────────────────────────────

_INDEED_LOCATIONS = ["Bangalore", "Mumbai", "Delhi", "Hyderabad", "Pune"]


def _scrape_indeed_page(page: Page, query: str, location: str) -> list[dict]:
    jobs: list[dict] = []
    params = f"q={query.replace(' ', '+')}&l={location.replace(' ', '+')}&fromage=14&sort=date"
    url = f"https://in.indeed.com/jobs?{params}"

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("div.job_seen_beacon, div[data-jk]", timeout=15000)
        time.sleep(random.uniform(1, 2))

        cards = page.query_selector_all("div.job_seen_beacon")
        logger.info(f"Indeed {location}: {len(cards)} raw cards")

        for card in cards[:25]:
            title_el   = card.query_selector("h2.jobTitle a, a[data-jk]")
            company_el = card.query_selector("span.companyName, a.companyName")
            loc_el     = card.query_selector("div.companyLocation")
            salary_el  = card.query_selector("div.metadata.salary-snippet-container, span.salary-snippet")
            date_el    = card.query_selector("span.date")
            desc_el    = card.query_selector("div.job-snippet")
            jk         = card.get_attribute("data-jk") or ""

            if not title_el:
                continue

            title   = title_el.inner_text().strip()
            company = company_el.inner_text().strip() if company_el else "Unknown"
            job_url = f"https://in.indeed.com/viewjob?jk={jk}" if jk else ""

            jobs.append({
                "title":       title,
                "company":     company,
                "location":    _norm_loc(loc_el.inner_text().strip() if loc_el else location),
                "source":      "indeed",
                "url":         job_url,
                "description": desc_el.inner_text().strip()[:500] if desc_el else "",
                "salary":      salary_el.inner_text().strip() if salary_el else "",
                "experience":  "",
                "posted_date": date_el.inner_text().strip() if date_el else "",
                "external_id": _ext_id("indeed", jk or title + company),
            })
    except PWTimeout:
        logger.warning(f"Indeed {location}: page timeout")
    except Exception as e:
        logger.error(f"Indeed {location}: {e}")

    return jobs


def scrape_indeed(query: str = "Product Manager") -> list[dict]:
    all_jobs: list[dict] = []
    with sync_playwright() as pw:
        browser = _new_browser(pw)
        ctx = _stealth_context(browser)
        page = ctx.new_page()
        for loc in _INDEED_LOCATIONS:
            all_jobs.extend(_scrape_indeed_page(page, query, loc))
            time.sleep(random.uniform(2, 3))
        browser.close()
    logger.info(f"Indeed total: {len(all_jobs)} jobs")
    return all_jobs


# ─── 3. Google Careers ────────────────────────────────────────────────────────

def scrape_google_careers(query: str = "Product Manager") -> list[dict]:
    """
    Scrapes careers.google.com — catches roles like the Google Pay / Google Play
    PM jobs that don't appear on LinkedIn.
    """
    jobs: list[dict] = []
    url = (
        f"https://www.google.com/about/careers/applications/jobs/results/"
        f"?q={query.replace(' ', '+')}&location=India"
    )

    with sync_playwright() as pw:
        browser = _new_browser(pw)
        ctx = _stealth_context(browser)
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("li.lLd3Je, div[jsname='x9k4EF']", timeout=15000)
            time.sleep(random.uniform(1, 2))

            cards = page.query_selector_all("li.lLd3Je")
            logger.info(f"Google Careers: {len(cards)} raw cards")

            for card in cards[:40]:
                title_el    = card.query_selector("h3.QJPWVe, h3")
                loc_el      = card.query_selector("span.r0wTof, div.Qk80Jf")
                company_el  = card.query_selector("span.j2uRTd")
                link_el     = card.query_selector("a")

                if not title_el:
                    continue

                title   = title_el.inner_text().strip()
                job_url = link_el.get_attribute("href") or ""
                if job_url.startswith("/"):
                    job_url = f"https://www.google.com{job_url}"
                raw_loc = loc_el.inner_text().strip() if loc_el else "India"

                jobs.append({
                    "title":       title,
                    "company":     "Google",
                    "location":    _norm_loc(raw_loc) if any(
                        k in raw_loc.lower() for k in _LOCATION_NORM
                    ) else raw_loc.split(";")[0].strip(),
                    "source":      "google_careers",
                    "url":         job_url,
                    "description": "",
                    "salary":      "",
                    "experience":  "",
                    "posted_date": "",
                    "external_id": _ext_id("google_careers", job_url or title),
                })
        except PWTimeout:
            logger.warning("Google Careers: page timeout")
        except Exception as e:
            logger.error(f"Google Careers: {e}")
        finally:
            browser.close()

    logger.info(f"Google Careers: {len(jobs)} jobs")
    return jobs


# ─── 4. Foundit (Monster India) ───────────────────────────────────────────────

_FOUNDIT_LOCATIONS = ["Bangalore", "Mumbai", "Delhi", "Hyderabad", "Pune"]


def scrape_foundit(query: str = "Product Manager") -> list[dict]:
    all_jobs: list[dict] = []

    with sync_playwright() as pw:
        browser = _new_browser(pw)
        ctx = _stealth_context(browser)
        page = ctx.new_page()

        for loc in _FOUNDIT_LOCATIONS:
            url = f"https://www.foundit.in/srp/results?query={query.replace(' ', '+')}&locations={loc}"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_selector("div.cardContainer, div.srpResultCardContainer", timeout=15000)
                time.sleep(random.uniform(1, 2))

                cards = page.query_selector_all("div.cardContainer, div.srpResultCardContainer")
                logger.info(f"Foundit {loc}: {len(cards)} raw cards")

                for card in cards[:25]:
                    title_el   = card.query_selector("h3.jobTitle a, a.jobTitle, div.title")
                    company_el = card.query_selector("span.companyName, a.companyName")
                    loc_el     = card.query_selector("span.location, div.location")
                    exp_el     = card.query_selector("span.experience")
                    salary_el  = card.query_selector("span.salary")
                    link_el    = card.query_selector("a[href*='/job/'], a[href*='/jobs/']")

                    if not title_el:
                        continue

                    title   = title_el.inner_text().strip()
                    job_url = (link_el.get_attribute("href") or "") if link_el else ""
                    if job_url.startswith("/"):
                        job_url = f"https://www.foundit.in{job_url}"

                    all_jobs.append({
                        "title":       title,
                        "company":     company_el.inner_text().strip() if company_el else "Unknown",
                        "location":    _norm_loc(loc_el.inner_text().strip() if loc_el else loc),
                        "source":      "foundit",
                        "url":         job_url,
                        "description": "",
                        "salary":      salary_el.inner_text().strip() if salary_el else "",
                        "experience":  exp_el.inner_text().strip() if exp_el else "",
                        "posted_date": "",
                        "external_id": _ext_id("foundit", job_url or title + loc),
                    })

                time.sleep(random.uniform(1.5, 2.5))
            except PWTimeout:
                logger.warning(f"Foundit {loc}: timeout")
            except Exception as e:
                logger.error(f"Foundit {loc}: {e}")

        browser.close()

    logger.info(f"Foundit total: {len(all_jobs)} jobs")
    return all_jobs
