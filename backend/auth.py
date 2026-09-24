"""Password hashing (bcrypt) and signed session tokens (JWT)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from db import User, get_session

TOKEN_TTL_DAYS = 14
ALGORITHM = "HS256"

# bcrypt silently truncates at 72 bytes, so reject longer input rather than
# letting two different long passwords authenticate the same account.
MAX_PASSWORD_BYTES = 72


def jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        # Dev fallback only. On Render this must be set, or every redeploy logs everyone out.
        return "dev-only-insecure-secret-change-me"
    return secret


def hash_password(password: str) -> str:
    """bcrypt embeds the salt in the returned hash string, so no separate salt column."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password must be at least 8 characters.")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password is too long (72 bytes max).")


def create_token(user_id: int, username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + timedelta(days=TOKEN_TTL_DAYS),
    }
    return jwt.encode(payload, jwt_secret(), algorithm=ALGORITHM)


def current_user(request: Request, session: Session = Depends(get_session)) -> User:
    """FastAPI dependency: resolve the Bearer token to a User, or 401."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in.")

    token = header.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, jwt_secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired. Please sign in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session.")

    user = session.get(User, int(payload.get("sub", 0)))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account no longer exists.")
    return user
