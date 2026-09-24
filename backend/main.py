"""Yale SOM course explorer API desk.

Run from backend/:  uvicorn main:app --reload --port 8000
Open API docs:      http://127.0.0.1:8000/docs
Frontend (Vite):    http://127.0.0.1:5173
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from agent import run_agent
from auth import create_token, current_user, hash_password, validate_password, verify_password
from db import Chat, User, courses_available, get_session, init_db
from models import (
    AuthResponse, ChatHistory, ChatMessage, ChatRequest, ChatResponse, Credentials,
)
from tools import list_courses

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

app = FastAPI(title="Yale SOM Courses", version="0.2.0")

# In production Render serves the frontend from a different origin, so the allowed
# origins come from an env var; "*" stays the default for local development.
origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"ok": True, "courses": courses_available()}


# ---------- auth ----------

@app.post("/api/auth/register", response_model=AuthResponse)
def register(body: Credentials, session: Session = Depends(get_session)):
    username = body.username.strip()
    if session.query(User).filter(User.username == username).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is taken.")

    validate_password(body.password)
    user = User(username=username, password_hash=hash_password(body.password))
    session.add(user)
    session.commit()
    return AuthResponse(token=create_token(user.id, user.username), username=user.username)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(body: Credentials, session: Session = Depends(get_session)):
    user = session.query(User).filter(User.username == body.username.strip()).first()
    # Same message either way: revealing which half was wrong helps account enumeration.
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password.")
    return AuthResponse(token=create_token(user.id, user.username), username=user.username)


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return {"username": user.username, "id": user.id}


# ---------- catalog ----------

@app.get("/api/courses")
def courses(q: str | None = Query(default=None)):
    """Course grid for the React catalog (optional text filter). Public."""
    rows = list_courses(q)
    return {"count": len(rows), "courses": rows}


# ---------- chat ----------

def _split_tools(raw: str | None) -> list[str]:
    return [t for t in (raw or "").split(",") if t]


@app.get("/api/chat/history", response_model=ChatHistory)
def history(user: User = Depends(current_user), session: Session = Depends(get_session)):
    rows = session.query(Chat).filter(Chat.user_id == user.id).order_by(Chat.id).all()
    return ChatHistory(messages=[
        ChatMessage(
            id=r.id, role=r.role, content=r.content,
            tools_used=_split_tools(r.tools_used), created_at=r.created_at,
        )
        for r in rows
    ])


@app.post("/api/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    session.add(Chat(user_id=user.id, role="user", content=body.message))
    session.commit()

    result = run_agent(body.message)
    reply = result.get("reply", "")
    tools_used = list(result.get("tools_used") or [])

    session.add(Chat(
        user_id=user.id, role="agent", content=reply, tools_used=",".join(tools_used),
    ))
    session.commit()

    return ChatResponse(reply=reply, tools_used=tools_used)


@app.delete("/api/chat/history")
def clear_history(user: User = Depends(current_user), session: Session = Depends(get_session)):
    deleted = session.query(Chat).filter(Chat.user_id == user.id).delete()
    session.commit()
    return {"deleted": deleted}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=int(os.getenv("PORT", "8000")), reload=False)
