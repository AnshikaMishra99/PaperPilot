"""/api/settings -- view and update runtime settings like API key and provider."""

from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..config import BACKEND_ROOT, settings
from ..rag.embeddings import reset_embedder
from ..rag.pipeline import llm_configured, reset_llm

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsOut(BaseModel):
    llm_configured: bool
    gemini_model: str
    embedding_provider: str


class SettingsUpdate(BaseModel):
    google_api_key: str | None = Field(default=None, description="Google AI Studio API key")
    embedding_provider: Literal["google", "local"] | None = None


def _update_env_file(updates: dict[str, str]) -> None:
    env_path = BACKEND_ROOT / ".env"
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    for key, val in updates.items():
        pattern = re.compile(rf"^{key}=.*$")
        matched = False
        new_lines = []
        for line in lines:
            if pattern.match(line):
                new_lines.append(f"{key}={val}")
                matched = True
            else:
                new_lines.append(line)
        if not matched:
            new_lines.append(f"{key}={val}")
        lines = new_lines

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@router.get("", response_model=SettingsOut)
async def get_settings_status() -> SettingsOut:
    return SettingsOut(
        llm_configured=llm_configured(),
        gemini_model=settings.gemini_model,
        embedding_provider=settings.embedding_provider,
    )


@router.post("", response_model=SettingsOut)
async def update_settings(payload: SettingsUpdate) -> SettingsOut:
    env_updates: dict[str, str] = {}

    if payload.google_api_key is not None:
        clean_key = payload.google_api_key.strip()
        settings.google_api_key = clean_key
        env_updates["GOOGLE_API_KEY"] = clean_key
        reset_llm()
        reset_embedder()

    if payload.embedding_provider is not None:
        settings.embedding_provider = payload.embedding_provider
        env_updates["EMBEDDING_PROVIDER"] = payload.embedding_provider
        reset_embedder()

    if env_updates:
        _update_env_file(env_updates)

    return SettingsOut(
        llm_configured=llm_configured(),
        gemini_model=settings.gemini_model,
        embedding_provider=settings.embedding_provider,
    )
