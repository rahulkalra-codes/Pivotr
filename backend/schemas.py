from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models import JobStatus


class JobBase(BaseModel):
    title: str
    company: str
    location: Optional[str] = "Bangalore"
    source: Optional[str] = "manual"
    url: Optional[str] = None
    description: Optional[str] = None
    salary: Optional[str] = None
    experience: Optional[str] = None
    status: Optional[JobStatus] = JobStatus.WISHLIST
    notes: Optional[str] = ""
    posted_date: Optional[str] = None


class JobCreate(JobBase):
    external_id: Optional[str] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    salary: Optional[str] = None
    experience: Optional[str] = None
    status: Optional[JobStatus] = None
    notes: Optional[str] = None
    posted_date: Optional[str] = None


class JobResponse(JobBase):
    id: int
    scraped_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    external_id: Optional[str] = None
    relevance_score: Optional[int] = None

    model_config = {"from_attributes": True}


class ScrapeResult(BaseModel):
    added: int
    skipped: int
    errors: int
    message: str
