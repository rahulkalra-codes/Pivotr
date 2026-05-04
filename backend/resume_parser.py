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
    Higher = more relevant.
    """
    score = 50  # baseline

    # Title match
    title_lower = job.get("title", "").lower()
    if "product manager" in title_lower:
        score += 20
    elif "product" in title_lower:
        score += 10

    # Experience level match
    yoe = resume.get("years_experience")
    exp_text = job.get("experience", "").lower()
    if yoe is not None and exp_text:
        # Extract required years from job experience field
        exp_match = re.search(r"(\d+)\s*(?:-\s*(\d+))?\s*(?:years?|yrs?)", exp_text)
        if exp_match:
            min_exp = int(exp_match.group(1))
            max_exp = int(exp_match.group(2)) if exp_match.group(2) else min_exp + 4
            if min_exp <= yoe <= max_exp:
                score += 20
            elif yoe < min_exp:
                score -= 15
            elif yoe > max_exp + 3:
                score -= 5

    # Skill overlap
    resume_skills = set(resume.get("skills", []))
    desc_lower = (job.get("description", "") + " " + job.get("title", "")).lower()
    skill_hits = sum(1 for s in resume_skills if s in desc_lower)
    score += min(skill_hits * 3, 15)

    return max(0, min(100, score))
