"""
Security & Data Minimization Core
Manages cryptographic tokens, auth headers, and privacy enforcement.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from backend.config import settings


def create_access_token(user_id: str, display_name: str, expires_delta: Optional[timedelta] = None) -> str:
    """Generates signed JWT for authenticated user session."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.session_token_expire_minutes)
    )
    to_encode = {
        "sub": user_id,
        "name": display_name,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_access_token(token: str) -> Optional[dict]:
    """Validates JWT signature and expiry. Returns decoded claims or None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except Exception:
        return None
