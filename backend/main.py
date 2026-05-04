import io
import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models
from auth import create_access_token, get_current_user, hash_password, verify_password
from database import Base, SessionLocal, engine, get_db
from models import Job, JobStatus, User
from resume_parser import parse_resume_text, score_job
from schemas import JobCreate, JobResponse, JobUpdate, ScrapeResult, TokenResponse, UserCreate, UserResponse
from scraper import run_all_scrapers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

SCRAPE_STATUS: dict = {"running": False, "last_result": None}


def _settings_path(user_id: int) -> str:
    return f"settings_{user_id}.json"


def _resume_cache_path(user_id: int) -> str:
    return f"resume_cache_{user_id}.json"


def _load_settings(user_id: int) -> dict:
    path = _settings_path(user_id)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _save_settings(user_id: int, data: dict):
    with open(_settings_path(user_id), "w") as f:
        json.dump(data, f)


def _load_resume_cache(user_id: int) -> dict:
    path = _resume_cache_path(user_id)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _save_resume_cache(user_id: int, data: dict):
    with open(_resume_cache_path(user_id), "w") as f:
        json.dump(data, f)


def save_scraped_jobs(jobs: list[dict], user_id: int) -> dict:
    db = SessionLocal()
    added = skipped = errors = 0
    try:
        for job_data in jobs:
            ext_id = job_data.get("external_id")
            if ext_id and db.query(Job).filter(
                Job.external_id == ext_id, Job.user_id == user_id
            ).first():
                skipped += 1
                continue
            try:
                filtered = {k: v for k, v in job_data.items() if hasattr(Job, k)}
                filtered["user_id"] = user_id
                job = Job(**filtered)
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Scheduled scrape is disabled — no global user context available
    logger.info("Pivotr API started (scheduled scrape disabled in multi-user mode)")
    yield


app = FastAPI(title="Pivotr API", lifespan=lifespan)

_frontend_url = os.getenv("FRONTEND_URL", "")
_allowed_origins = ["http://localhost:5173", "http://localhost:3000"]
if _frontend_url:
    _allowed_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Auth ─────────────────────────────────────────────────────────────────────

@app.post("/api/auth/register", response_model=TokenResponse, status_code=201)
def register(body: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=body.email, hashed_password=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(id=user.id, email=user.email),
    )


@app.post("/api/auth/login", response_model=TokenResponse)
def login(body: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(id=user.id, email=user.email),
    )


@app.get("/api/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse(id=current_user.id, email=current_user.email)


# ─── Jobs ──────────────────────────────────────────────────────────────────────

@app.get("/api/jobs", response_model=list[JobResponse])
def list_jobs(
    status: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Job).filter(Job.user_id == current_user.id)
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
    resume = _load_resume_cache(current_user.id)
    if resume:
        for job in jobs:
            job.relevance_score = score_job(
                {"title": job.title, "experience": job.experience or "", "description": job.description or ""},
                resume,
            )

    return jobs


@app.post("/api/jobs", response_model=JobResponse, status_code=201)
def create_job(
    job: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_job = Job(**job.model_dump(exclude_unset=True), user_id=current_user.id)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.patch("/api/jobs/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    updates: JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return job


@app.delete("/api/jobs/{job_id}", status_code=204)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()


# ─── Resume ────────────────────────────────────────────────────────────────────

@app.post("/api/resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
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
    _save_resume_cache(current_user.id, parsed)

    return {
        "message": "Resume uploaded and parsed successfully",
        "years_experience": parsed.get("years_experience"),
        "skills_found": len(parsed.get("skills", [])),
        "skills": parsed.get("skills", []),
        "current_title": parsed.get("current_title"),
    }


@app.get("/api/resume")
def get_resume(current_user: User = Depends(get_current_user)):
    resume = _load_resume_cache(current_user.id)
    if not resume:
        return {"uploaded": False}
    return {"uploaded": True, **resume}


@app.delete("/api/resume", status_code=204)
def delete_resume(current_user: User = Depends(get_current_user)):
    path = _resume_cache_path(current_user.id)
    if os.path.exists(path):
        os.remove(path)


# ─── Scraping ─────────────────────────────────────────────────────────────────

def _do_scrape_background(user_id: int):
    SCRAPE_STATUS["running"] = True
    SCRAPE_STATUS["last_result"] = None
    try:
        jobs = run_all_scrapers()
        result = save_scraped_jobs(jobs, user_id)
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
def trigger_scrape(current_user: User = Depends(get_current_user)):
    if SCRAPE_STATUS["running"]:
        return {"status": "running", "message": "Scrape already in progress…"}
    thread = threading.Thread(target=_do_scrape_background, args=(current_user.id,), daemon=True)
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
def set_linkedin_cookie(
    body: dict,
    current_user: User = Depends(get_current_user),
):
    settings = _load_settings(current_user.id)
    cookie = body.get("cookie", "").strip()
    settings["linkedin_cookie"] = cookie
    _save_settings(current_user.id, settings)
    return {"status": "saved", "set": bool(cookie)}


@app.get("/api/settings/linkedin-cookie")
def get_linkedin_cookie(current_user: User = Depends(get_current_user)):
    settings = _load_settings(current_user.id)
    cookie = settings.get("linkedin_cookie", "")
    return {"set": bool(cookie), "preview": cookie[:12] + "..." if cookie else ""}


@app.delete("/api/settings/linkedin-cookie", status_code=204)
def delete_linkedin_cookie(current_user: User = Depends(get_current_user)):
    settings = _load_settings(current_user.id)
    settings.pop("linkedin_cookie", None)
    _save_settings(current_user.id, settings)


# ─── Stats ────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base_q = db.query(Job).filter(Job.user_id == current_user.id)
    total = base_q.count()
    by_status = {
        s.value: base_q.filter(Job.status == s.value).count()
        for s in JobStatus
    }
    return {
        "total": total,
        "by_status": by_status,
        "sources": {
            src: base_q.filter(Job.source == src).count()
            for src in ["linkedin", "indeed", "google_careers", "manual"]
        },
    }


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}
