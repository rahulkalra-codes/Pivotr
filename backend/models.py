from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
import enum
from database import Base


class JobStatus(str, enum.Enum):
    WISHLIST = "Wishlist"
    APPLIED = "Applied"
    INTERVIEWING = "Interviewing"
    OFFER = "Offer"
    REJECTED = "Rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), default="Bangalore")
    source = Column(String(50))  # "naukri" | "google_jobs" | "manual"
    url = Column(Text)
    description = Column(Text)
    salary = Column(String(255))
    experience = Column(String(100))
    status = Column(String(50), default=JobStatus.WISHLIST)
    notes = Column(Text, default="")
    posted_date = Column(String(100))
    scraped_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    external_id = Column(String(255), index=True)  # dedup key, per-user (no longer globally unique)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
