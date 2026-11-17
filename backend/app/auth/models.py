"""SQLAlchemy and Pydantic models for persistent user authentication."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Generator

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from ..config import settings

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False, default="")
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        db_path = settings.users_db_file
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def init_db() -> None:
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    session_factory = get_sessionmaker()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


# --- Pydantic Schemas ----------------------------------------------------


class UserRegister(BaseModel):
    email: str = Field(..., min_length=3, description="User email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    full_name: str = Field(default="", description="Full display name")


class UserLogin(BaseModel):
    email: str = Field(..., min_length=3, description="User email address")
    password: str = Field(..., description="Password")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
