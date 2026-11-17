"""Application settings.

Everything configurable lives here and is read from environment variables
(or a local `.env` file). No secret is ever hard-coded, and no secret is ever
sent to the browser -- the frontend only ever talks to this backend.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM -------------------------------------------------------------
    google_api_key: str = ""
    gemini_model: str = "models/gemini-flash-latest"

    # --- Embeddings ------------------------------------------------------
    # "google" uses the Gemini embedding API; "local" runs a small
    # sentence-transformers or ONNX model on the host machine.
    embedding_provider: str = "google"
    google_embedding_model: str = "models/gemini-embedding-001"
    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Storage ---------------------------------------------------------
    chroma_dir: str = "./data/chroma"
    upload_dir: str = "./data/uploads"
    registry_path: str = "./data/documents.json"
    users_db_path: str = "./data/users.db"

    # --- Authentication (PyJWT + pwdlib Argon2) --------------------------
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24 * 7  # 7 days

    # --- Ingestion / retrieval tuning ------------------------------------
    max_upload_mb: int = 25
    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 6
    # Cosine distance cut-off. Chroma returns distance (0 = identical).
    # Chunks further away than this are treated as "not relevant".
    max_distance: float = 0.85

    # --- HTTP ------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Derived helpers -------------------------------------------------
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def _resolve(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (BACKEND_ROOT / path).resolve()

    @property
    def chroma_path(self) -> Path:
        return self._resolve(self.chroma_dir)

    @property
    def upload_path(self) -> Path:
        return self._resolve(self.upload_dir)

    @property
    def registry_file(self) -> Path:
        return self._resolve(self.registry_path)

    @property
    def users_db_file(self) -> Path:
        return self._resolve(self.users_db_path)

    def ensure_directories(self) -> None:
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self.upload_path.mkdir(parents=True, exist_ok=True)
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self.users_db_file.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings


settings = get_settings()
