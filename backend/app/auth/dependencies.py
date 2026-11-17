"""FastAPI dependencies for JWT authentication and current user resolution."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session

from .models import User, get_db
from .utils import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency that requires a valid Bearer token and returns the corresponding User."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please sign in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


async def get_optional_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Optional user dependency that returns None if token is absent or invalid."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None
