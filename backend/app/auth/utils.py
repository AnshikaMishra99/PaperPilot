"""Cryptographic utilities: modern Argon2 password hashing (pwdlib) and PyJWT tokens."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from ..config import settings

logger = logging.getLogger("paperpilot.auth")

# Recommended password hashing algorithm: Argon2id via pwdlib
_password_hash = PasswordHash.recommended()

_FALLBACK_SECRET = "insecure-fallback-datapilot-jwt-secret-key-32bytes-min"


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2."""
    return _password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2 hash."""
    return _password_hash.verify(plain_password, hashed_password)


def get_jwt_secret() -> str:
    """Retrieve the JWT signing secret from settings or warn and use fallback."""
    secret = settings.jwt_secret.strip() if settings.jwt_secret else ""
    if not secret:
        logger.warning(
            "JWT_SECRET is not configured in .env! Using a fallback secret for development. "
            "Set JWT_SECRET in production for security."
        )
        return _FALLBACK_SECRET
    return secret


def create_access_token(
    user_id: str,
    email: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Generate a signed JWT access token with an expiration timestamp."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_expiration_minutes)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": now,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload=payload,
        key=get_jwt_secret(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a signed JWT access token."""
    return jwt.decode(
        token,
        key=get_jwt_secret(),
        algorithms=[settings.jwt_algorithm],
    )
