"""Copy the course catalog from the local SQLite file into Postgres (Supabase).

Usage (from backend/, with the venv active):

    DATABASE_URL="postgresql://postgres:PASSWORD@db.xxxx.supabase.co:5432/postgres" \
        .venv/bin/python seed_postgres.py

Only the courses table is copied. users and chats are created empty by the app on
startup, so real accounts are never moved between environments.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
SQLITE_PATH = ROOT / "data" / "yale_som.db"

COLUMNS = [
    "course_id", "course_number", "course_title", "course_category", "course_type",
    "section", "faculty", "faculty_email", "daytimes", "timings_day", "timings_start",
    "timings_end", "room", "units", "bid_or_permission", "course_description",
    "faculty_bio", "syllabus", "term_code", "visible",
]

CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS courses (
  row_id SERIAL PRIMARY KEY,
  {", ".join(f"{c} TEXT" for c in COLUMNS)}
)
"""


def main() -> None:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        sys.exit("DATABASE_URL is not set. Paste your Supabase connection string first.")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    lite = sqlite3.connect(SQLITE_PATH)
    lite.row_factory = sqlite3.Row
    rows = [
        {c: r[c] for c in COLUMNS}
        for r in lite.execute(f"SELECT {', '.join(COLUMNS)} FROM courses")
    ]
    lite.close()
    print(f"read {len(rows)} courses from {SQLITE_PATH.name}")

    engine = create_engine(url, future=True)
    placeholders = ", ".join(f":{c}" for c in COLUMNS)
    insert_sql = text(f"INSERT INTO courses ({', '.join(COLUMNS)}) VALUES ({placeholders})")

    with engine.begin() as conn:
        conn.execute(text(CREATE_SQL))
        # Reloading the catalog should replace it, not append a second copy.
        existing = conn.execute(text("SELECT COUNT(*) FROM courses")).scalar_one()
        if existing:
            print(f"courses table already has {existing} rows -> clearing before reload")
            conn.execute(text("DELETE FROM courses"))
        conn.execute(insert_sql, rows)

    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM courses")).scalar_one()
        visible = conn.execute(
            text("SELECT COUNT(*) FROM courses WHERE visible = '1'")
        ).scalar_one()

    print(f"Postgres now has {total} courses ({visible} visible). Done.")


if __name__ == "__main__":
    main()
