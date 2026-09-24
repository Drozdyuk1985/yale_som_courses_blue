"""Pydantic data objects shared by tools.py, agent.py and main.py."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Course(BaseModel):
    """One row of the courses table, trimmed to the fields the agent reasons over."""

    course_id: str = ""
    number: str = ""
    title: str = ""
    category: str = ""
    course_type: str = ""
    section: str = ""
    faculty: str = ""
    faculty_email: str = ""
    daytimes: str = ""
    room: str = ""
    units: str = ""
    bid_or_permission: str = ""
    syllabus: str = ""
    description: str = ""
    faculty_bio: str = ""


class CourseSearchResult(BaseModel):
    total_matches: int
    returned: int
    courses: list[Course]


class AgentResult(BaseModel):
    reply: str
    tools_used: list[str] = Field(default_factory=list)


# ---------- auth ----------

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8)


class AuthResponse(BaseModel):
    token: str
    username: str


# ---------- chat ----------

class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    id: int
    role: str
    content: str
    tools_used: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class ChatHistory(BaseModel):
    messages: list[ChatMessage]
