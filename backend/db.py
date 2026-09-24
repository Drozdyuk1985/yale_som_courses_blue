"""Database layer. SQLite locally, Supabase Postgres in production.

DATABASE_URL selects the backend. When it is unset we fall back to the bundled
SQLite file, so the app still runs on a laptop with no configuration.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, String, Text, create_engine, text,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

ROOT = Path(__file__).resolve().parent.parent
SQLITE_PATH = ROOT / "data" / "yale_som.db"


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{SQLITE_PATH}"
    # Supabase and Render hand out postgres:// URLs; SQLAlchemy 2 wants an explicit driver.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


URL = database_url()
IS_SQLITE = URL.startswith("sqlite")

engine = create_engine(
    URL,
    echo=False,
    future=True,
    pool_pre_ping=not IS_SQLITE,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(16), nullable=False)          # 'user' | 'agent'
    content = Column(Text, nullable=False)
    tools_used = Column(Text, default="")              # comma-separated
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="chats")


def get_session() -> Session:
    """FastAPI dependency: one session per request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


COURSES_DDL = """
CREATE TABLE IF NOT EXISTS courses (
  row_id SERIAL PRIMARY KEY,
  course_id TEXT, course_number TEXT, course_title TEXT, course_category TEXT,
  course_type TEXT, section TEXT, faculty TEXT, faculty_email TEXT,
  daytimes TEXT, timings_day TEXT, timings_start TEXT, timings_end TEXT,
  room TEXT, units TEXT, bid_or_permission TEXT, course_description TEXT,
  faculty_bio TEXT, syllabus TEXT, term_code TEXT, visible TEXT
)
"""


def init_db() -> None:
    """Create users/chats if missing. The courses table is loaded from the course data."""
    Base.metadata.create_all(engine)
    if not IS_SQLITE:
        # On a fresh Postgres instance the courses table may not exist yet.
        with engine.begin() as conn:
            conn.execute(text(COURSES_DDL))


def courses_available() -> int:
    with engine.connect() as conn:
        try:
            return conn.execute(text("SELECT COUNT(*) FROM courses")).scalar_one()
        except Exception:
            return 0
