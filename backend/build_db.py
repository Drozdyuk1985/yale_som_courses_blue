"""One-off: build data/yale_som.db (courses + users + chats) from the course JSON.

Safe to re-run: it recreates only the courses table and leaves users/chats alone.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "data" / "yale_som_classes.json"
DB_PATH = ROOT / "data" / "yale_som.db"

COLUMNS = [
    ("course_id", "Course ID"),
    ("course_number", "Course Number"),
    ("course_title", "Course Title"),
    ("course_category", "Course Category"),
    ("course_type", "Course Type"),
    ("section", "Section"),
    ("faculty", "Faculty 1"),
    ("faculty_email", "Faculty 1 Email"),
    ("daytimes", "Daytimes"),
    ("timings_day", "Timings Day"),
    ("timings_start", "Timings StartTime"),
    ("timings_end", "Timings EndTime"),
    ("room", "Room"),
    ("units", "Units"),
    ("bid_or_permission", "Bid Or Permission"),
    ("course_description", "Course Description"),
    ("faculty_bio", "faculty_bio"),
    ("syllabus", "Syllabus"),
    ("term_code", "TermCode"),
    ("visible", "Visible"),
]

def main() -> None:
    records = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS courses")
    cols_sql = ",\n  ".join(f"{name} TEXT" for name, _ in COLUMNS)
    cur.execute(f"CREATE TABLE courses (\n  row_id INTEGER PRIMARY KEY AUTOINCREMENT,\n  {cols_sql}\n)")

    rows = [tuple(str(rec.get(src) or "") for _, src in COLUMNS) for rec in records]
    placeholders = ", ".join("?" for _ in COLUMNS)
    cur.executemany(
        f"INSERT INTO courses ({', '.join(n for n, _ in COLUMNS)}) VALUES ({placeholders})",
        rows,
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_courses_number ON courses(course_number)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_courses_faculty ON courses(faculty)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_courses_category ON courses(course_category)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chats (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          role TEXT NOT NULL,
          content TEXT NOT NULL,
          tools_used TEXT DEFAULT '',
          created_at TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chats_user ON chats(user_id, id)")

    conn.commit()
    total = cur.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    visible = cur.execute("SELECT COUNT(*) FROM courses WHERE visible = '1'").fetchone()[0]
    print(f"courses rows : {total}")
    print(f"visible='1'  : {visible}")
    conn.close()
    print("wrote", DB_PATH)

if __name__ == "__main__":
    main()
