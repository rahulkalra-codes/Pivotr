"""
Resume parser — extracts years of experience, skills, and title from uploaded PDF/text.
Uses heuristics only (no external AI API) so it works offline.
"""

import re
import io
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

PM_SKILLS = [
    "product management", "product roadmap", "product strategy", "user research",
    "a/b testing", "agile", "scrum", "jira", "confluence", "figma", "sketch",
    "data analysis", "sql", "python", "go-to-market", "gtm", "market research",
    "competitive analysis", "ux", "ui", "wireframing", "prototyping",
    "stakeholder management", "cross-functional", "okrs", "kpis", "metrics",
    "growth", "monetization", "pricing", "customer discovery", "mvp",
    "backlog", "sprint", "user stories", "acceptance criteria", "p&l",
]

EXPERIENCE_PATTERNS = [
    r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:work\s+)?experience",
    r"experience[:\s]+(\d+)\+?\s*(?:years?|yrs?)",
    r"(\d+)\+?\s*(?:years?|yrs?)\s+in\s+product",
]

DATE_RANGE_PATTERN = re.compile(
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"[\s,]*(\d{4})\s*(?:–|-|to)\s*"
    r"(present|current|jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"[\s,]*(\d{4})?",
    re.IGNORECASE,
)

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _months_from_range(start_m: str, start_y: int, end_m: Optional[str], end_y: Optional[int]) -> int:
    sm = MONTH_MAP.get(start_m[:3].lower(), 1)
    now = datetime.now()
    if end_m is None or (isinstance(end_m, str) and end_m.lower() in ("present", "current")):
        ey, em = now.year, now.month
    else:
        em = MONTH_MAP.get(end_m[:3].lower(), 1)
        ey = end_y or now.year
    return max(0, (ey - start_y) * 12 + (em - sm))


def _extract_years_from_dates(text: str) -> float:
    total_months = 0
    for m in DATE_RANGE_PATTERN.finditer(text):
        sm, sy, em, ey = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        ey_int = int(ey) if ey and ey.isdigit() else None
        total_months += _months_from_range(sm, sy, em, ey_int)
    return round(total_months / 12, 1)


def _extract_years_explicit(text: str) -> Optional[float]:
    for pat in EXPERIENCE_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return None


def _extract_skills(text: str) -> list[str]:
    text_lower = text.lower()
    return [s for s in PM_SKILLS if s in text_lower]


def _extract_current_title(text: str) -> str:
    patterns = [
        r"(?:current(?:ly)?|present)\s+(?:role|position|title)[:\s]+([^\n]+)",
        r"(?:senior\s+)?product\s+manager[^\n]*",
        r"(?:vp|head|director|lead)[^\n]*product[^\n]*",
        r"(?:associate\s+)?product\s+manager[^\n]*",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:100]
    return "Product Manager"


def parse_resume_text(text: str) -> dict:
    explicit = _extract_years_explicit(text)
    date_derived = _extract_years_from_dates(text)

    years_exp = explicit if explicit is not None else (date_derived if date_derived > 0 else None)

    return {
        "years_experience": years_exp,
        "skills": _extract_skills(text),
        "current_title": _extract_current_title(text),
        "raw_length": len(text),
    }


def score_job(job: dict, resume: dict) -> int:
    """
    Returns 0–100 relevance score for a job given parsed resume data.
    Scores based on: title relevance (30), seniority match (40), skill overlap (30).
    """
    score = 0
    title_lower = job.get("title", "").lower()
    yoe = resume.get("years_experience") or 0

    # ── Title relevance (0–30) ────────────────────────────────────────────────
    if "product manager" in title_lower:
        score += 30
    elif "product" in title_lower and any(w in title_lower for w in ["lead", "head", "director", "vp", "owner"]):
        score += 25
    elif "product" in title_lower:
        score += 15

    # ── Seniority match with YoE (0–40) ──────────────────────────────────────
    # Determine seniority tier of the job
    if any(w in title_lower for w in ["vp ", "vice president", "head of product"]):
        job_tier = 5        # 12+ YoE
    elif any(w in title_lower for w in ["director", "group product"]):
        job_tier = 4        # 8–12 YoE
    elif any(w in title_lower for w in ["senior", "staff", "principal", "lead"]):
        job_tier = 3        # 5–8 YoE
    elif any(w in title_lower for w in ["product manager", "product owner"]) and \
         not any(w in title_lower for w in ["associate", "junior", "entry"]):
        job_tier = 2        # 2–5 YoE
    else:
        job_tier = 1        # 0–2 YoE (associate/junior)

    # Map user YoE to tier
    if yoe >= 12:
        user_tier = 5
    elif yoe >= 8:
        user_tier = 4
    elif yoe >= 5:
        user_tier = 3
    elif yoe >= 2:
        user_tier = 2
    else:
        user_tier = 1

    tier_diff = abs(job_tier - user_tier)
    if tier_diff == 0:
        score += 40
    elif tier_diff == 1:
        score += 25
    elif tier_diff == 2:
        score += 10
    # tier_diff >= 3: no seniority points (very mismatched)

    # ── Skill overlap in title + description (0–30) ───────────────────────────
    resume_skills = set(resume.get("skills", []))
    text_lower = (job.get("description", "") + " " + job.get("title", "")).lower()
    skill_hits = sum(1 for s in resume_skills if s in text_lower)
    score += min(skill_hits * 5, 30)

    return max(0, min(100, score))
