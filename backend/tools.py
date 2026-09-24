"""search_courses: the agent's course tool, now backed by the courses table.

web_search is not implemented here: it is OpenAI's native server-side web search,
wired in agent.py via pydantic_ai.capabilities.WebSearch.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text

from db import engine
from models import Course, CourseSearchResult

MAX_COURSE_RESULTS = 15

DAY_ALIASES = {
    "m": "M", "mo": "M", "mon": "M", "monday": "M",
    "t": "T", "tu": "T", "tue": "T", "tues": "T", "tuesday": "T",
    "w": "W", "we": "W", "wed": "W", "wednesday": "W",
    "th": "Th", "thu": "Th", "thur": "Th", "thurs": "Th", "thursday": "Th",
    "f": "F", "fr": "F", "fri": "F", "friday": "F",
}

SELECT_COLUMNS = """
  course_id, course_number, course_title, course_category, course_type, section,
  faculty, faculty_email, daytimes, room, units, bid_or_permission,
  course_description, faculty_bio, syllabus, timings_day, visible
"""

QUERY_FIELDS = (
    "course_title", "course_number", "course_description",
    "faculty", "course_category", "faculty_bio",
)


def _day_tokens(row: dict[str, Any]) -> set[str]:
    # "M  W 10:05 AM-11:25 AM" -> day letters sit before the first digit.
    head = re.split(r"\d", str(row.get("daytimes") or ""), maxsplit=1)[0]
    tokens = {DAY_ALIASES.get(part.lower(), "") for part in head.split()}
    # timings_day is filled in for only ~25 of 234 rows, so it is a fallback.
    tokens |= {
        DAY_ALIASES.get(part.strip().lower(), "")
        for part in str(row.get("timings_day") or "").split(",")
    }
    return {token for token in tokens if token}


def _to_course(row: dict[str, Any]) -> Course:
    return Course(
        course_id=str(row.get("course_id") or ""),
        number=str(row.get("course_number") or ""),
        title=str(row.get("course_title") or ""),
        category=str(row.get("course_category") or ""),
        course_type=str(row.get("course_type") or ""),
        section=str(row.get("section") or ""),
        faculty=str(row.get("faculty") or ""),
        faculty_email=str(row.get("faculty_email") or ""),
        daytimes=str(row.get("daytimes") or ""),
        room=str(row.get("room") or ""),
        units=str(row.get("units") or ""),
        bid_or_permission=str(row.get("bid_or_permission") or ""),
        syllabus=str(row.get("syllabus") or ""),
        description=str(row.get("course_description") or "").strip()[:600],
        faculty_bio=str(row.get("faculty_bio") or "").strip()[:400],
    )


def search_courses(
    query: str | None = None,
    title: str | None = None,
    number: str | None = None,
    faculty: str | None = None,
    category: str | None = None,
    day: str | None = None,
    course_type: str | None = None,
    include_hidden: bool = False,
    limit: int = MAX_COURSE_RESULTS,
) -> CourseSearchResult:
    """Search the Yale SOM course catalog.

    All filters are case-insensitive substring matches and combine with AND.
    query searches title, number, description, faculty and faculty bio together.
    day accepts Monday/Mon/M style input and matches scheduled meeting days.
    """
    clauses: list[str] = []
    params: dict[str, Any] = {}

    if not include_hidden:
        clauses.append("visible = '1'")

    for value, column in (
        (title, "course_title"),
        (number, "course_number"),
        (faculty, "faculty"),
        (category, "course_category"),
        (course_type, "course_type"),
    ):
        if value:
            key = f"p_{column}"
            clauses.append(f"LOWER({column}) LIKE :{key}")
            params[key] = f"%{value.lower()}%"

    if query:
        ors = " OR ".join(f"LOWER({field}) LIKE :p_query" for field in QUERY_FIELDS)
        clauses.append(f"({ors})")
        params["p_query"] = f"%{query.lower()}%"

    where = " AND ".join(clauses) if clauses else "1=1"
    sql = f"SELECT {SELECT_COLUMNS} FROM courses WHERE {where} ORDER BY course_number, section"

    with engine.connect() as conn:
        rows = [dict(r) for r in conn.execute(text(sql), params).mappings()]

    # Day filtering stays in Python: the schedule string needs parsing that SQL LIKE
    # cannot do safely (a LIKE '%T%' match would also catch "Th").
    wanted_day = DAY_ALIASES.get((day or "").strip().lower())
    if day:
        rows = [r for r in rows if wanted_day and wanted_day in _day_tokens(r)]

    capped = max(1, min(limit, MAX_COURSE_RESULTS))
    courses = [_to_course(r) for r in rows[:capped]]
    return CourseSearchResult(
        total_matches=len(rows), returned=len(courses), courses=courses
    )


def list_courses(q: str | None = None) -> list[dict[str, Any]]:
    """Catalog grid feed for the React app."""
    sql = f"SELECT {SELECT_COLUMNS} FROM courses WHERE visible = '1'"
    params: dict[str, Any] = {}

    if q and q.strip():
        ors = " OR ".join(f"LOWER({field}) LIKE :q" for field in QUERY_FIELDS)
        sql += f" AND ({ors})"
        params["q"] = f"%{q.strip().lower()}%"

    sql += " ORDER BY course_number, section"
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(text(sql), params).mappings()]
