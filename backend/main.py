import io
import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models
from database import Base, SessionLocal, engine, get_db
from models import Job, JobStatus
from resume_parser import parse_resume_text, score_job
from schemas import JobCreate, JobResponse, JobUpdate, ScrapeResult
from scraper import run_all_scrapers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

scheduler = BackgroundScheduler()
RESUME_CACHE_PATH = "resume_cache.json"
SETTINGS_PATH = "settings.json"
SCRAPE_STATUS: dict = {"running": False, "last_result": None}


def _load_settings() -> dict:
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    return {}


def _save_settings(data: dict):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(data, f)


def _load_resume_cache() -> dict:
    if os.path.exists(RESUME_CACHE_PATH):
        with open(RESUME_CACHE_PATH) as f:
            return json.load(f)
    return {}


def _save_resume_cache(data: dict):
    with open(RESUME_CACHE_PATH, "w") as f:
        json.dump(data, f)


def save_scraped_jobs(jobs: list[dict]) -> dict:
    db = SessionLocal()
    added = skipped = errors = 0
    try:
        for job_data in jobs:
            ext_id = job_data.get("external_id")
            if ext_id and db.query(Job).filter(Job.external_id == ext_id).first():
                skipped += 1
                continue
            try:
                job = Job(**{k: v for k, v in job_data.items() if hasattr(Job, k)})
                db.add(job)
                db.commit()
                added += 1
            except Exception as e:
                db.rollback()
                logger.error(f"Error saving job: {e}")
                errors += 1
    finally:
        db.close()
    return {"added": added, "skipped": skipped, "errors": errors}


def scheduled_scrape():
    logger.info("Running scheduled scrape...")
    jobs = run_all_scrapers()
    result = save_scraped_jobs(jobs)
    logger.info(f"Scrape done: {result}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(scheduled_scrape, "cron", hour=8, minute=0, id="daily_scrape")
    scheduler.start()
    logger.info("Scheduler started — daily scrape at 08:00")
    yield
    scheduler.shutdown()


app = FastAPI(title="Pivotr API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Jobs ──────────────────────────────────────────────────────────────────────

@app.get("/api/jobs", response_model=list[JobResponse])
def list_jobs(
    status: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Job)
    if status:
        q = q.filter(Job.status == status)
    if company:
        q = q.filter(Job.company.ilike(f"%{company}%"))
    if location and location.lower() != "all":
        if location.lower() == "rest of india":
            q = q.filter(
                ~Job.location.ilike("%bangalore%")
                & ~Job.location.ilike("%remote%")
            )
        elif location.lower() == "remote":
            q = q.filter(Job.location.ilike("%remote%"))
        else:
            q = q.filter(Job.location.ilike(f"%{location}%"))
    if source:
        q = q.filter(Job.source == source)
    if search:
        q = q.filter(
            Job.title.ilike(f"%{search}%") | Job.company.ilike(f"%{search}%")
        )
    jobs = q.order_by(Job.scraped_at.desc()).all()

    # Fix double-slash URLs left by earlier scraper versions
    for job in jobs:
        if job.url and job.url.endswith("//"):
            job.url = job.url.rstrip("/")

    # Attach relevance score if resume is uploaded
    resume = _load_resume_cache()
    if resume:
        for job in jobs:
            job.relevance_score = score_job(
                {"title": job.title, "experience": job.experience or "", "description": job.description or ""},
                resume,
            )

    return jobs


@app.post("/api/jobs", response_model=JobResponse, status_code=201)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    db_job = Job(**job.model_dump(exclude_unset=True))
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.patch("/api/jobs/{job_id}", response_model=JobResponse)
def update_job(job_id: int, updates: JobUpdate, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return job


@app.delete("/api/jobs/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()


# ─── Resume ────────────────────────────────────────────────────────────────────

@app.post("/api/resume")
async def upload_resume(file: UploadFile = File(...)):
    content = await file.read()

    if file.filename and file.filename.lower().endswith(".pdf"):
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            text = content.decode("utf-8", errors="ignore")
    else:
        text = content.decode("utf-8", errors="ignore")

    parsed = parse_resume_text(text)
    _save_resume_cache(parsed)

    return {
        "message": "Resume uploaded and parsed successfully",
        "years_experience": parsed.get("years_experience"),
        "skills_found": len(parsed.get("skills", [])),
        "skills": parsed.get("skills", []),
        "current_title": parsed.get("current_title"),
    }


@app.get("/api/resume")
def get_resume():
    resume = _load_resume_cache()
    if not resume:
        return {"uploaded": False}
    return {"uploaded": True, **resume}


@app.delete("/api/resume", status_code=204)
def delete_resume():
    if os.path.exists(RESUME_CACHE_PATH):
        os.remove(RESUME_CACHE_PATH)


# ─── Scraping ─────────────────────────────────────────────────────────────────

def _do_scrape_background():
    SCRAPE_STATUS["running"] = True
    SCRAPE_STATUS["last_result"] = None
    try:
        jobs = run_all_scrapers()
        result = save_scraped_jobs(jobs)
        SCRAPE_STATUS["last_result"] = {
            "added": result["added"],
            "skipped": result["skipped"],
            "errors": result["errors"],
            "message": f"Done — {result['added']} new jobs added from {len(jobs)} scraped.",
        }
        logger.info(SCRAPE_STATUS["last_result"]["message"])
    except Exception as e:
        SCRAPE_STATUS["last_result"] = {"added": 0, "skipped": 0, "errors": 1, "message": str(e)}
        logger.error(f"Background scrape error: {e}")
    finally:
        SCRAPE_STATUS["running"] = False


@app.post("/api/scrape")
def trigger_scrape():
    if SCRAPE_STATUS["running"]:
        return {"status": "running", "message": "Scrape already in progress…"}
    thread = threading.Thread(target=_do_scrape_background, daemon=True)
    thread.start()
    return {"status": "started", "message": "Scraping started in background — results update automatically."}


@app.get("/api/scrape/status")
def scrape_status():
    return {
        "running": SCRAPE_STATUS["running"],
        "last_result": SCRAPE_STATUS["last_result"],
    }


# ─── LinkedIn Cookie ──────────────────────────────────────────────────────────

@app.post("/api/settings/linkedin-cookie")
def set_linkedin_cookie(body: dict):
    settings = _load_settings()
    cookie = body.get("cookie", "").strip()
    settings["linkedin_cookie"] = cookie
    _save_settings(settings)
    return {"status": "saved", "set": bool(cookie)}


@app.get("/api/settings/linkedin-cookie")
def get_linkedin_cookie():
    settings = _load_settings()
    cookie = settings.get("linkedin_cookie", "")
    return {"set": bool(cookie), "preview": cookie[:12] + "..." if cookie else ""}


@app.delete("/api/settings/linkedin-cookie", status_code=204)
def delete_linkedin_cookie():
    settings = _load_settings()
    settings.pop("linkedin_cookie", None)
    _save_settings(settings)


# ─── Stats ────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Job).count()
    by_status = {
        s.value: db.query(Job).filter(Job.status == s.value).count()
        for s in JobStatus
    }
    return {
        "total": total,
        "by_status": by_status,
        "sources": {
            src: db.query(Job).filter(Job.source == src).count()
            for src in ["linkedin", "indeed", "google_careers", "manual"]
        },
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}
