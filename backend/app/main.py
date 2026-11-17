"""FastAPI entrypoint.

Run with:  uvicorn app.main:app --reload --port 8000
Docs at:   http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes_chat import router as chat_router
from .api.routes_documents import router as documents_router
from .api.routes_settings import router as settings_router
from .auth import User, get_optional_current_user, init_db, router as auth_router
from .config import settings
from .errors import register_error_handlers
from .rag.pipeline import llm_configured
from .rag.vector_store import get_vector_store
from .schemas import HealthResponse
from .services import document_service

# Initialize SQLite database for persistent user authentication
init_db()

app = FastAPI(
    title="PaperPilot API",
    description="Retrieval-augmented question answering over uploaded research papers.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

register_error_handlers(app)

# Authentication endpoints mounted at both /auth and /api/auth
app.include_router(auth_router, prefix="/auth")
app.include_router(auth_router, prefix="/api/auth")

app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(settings_router)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health(
    current_user: User | None = Depends(get_optional_current_user),
) -> HealthResponse:
    """Everything the frontend needs to explain the system's state to a user."""
    try:
        chunks = get_vector_store().count()
    except Exception:
        chunks = 0

    user_docs = len(document_service.list_documents(current_user.id)) if current_user else len(document_service.list_documents())

    return HealthResponse(
        status="ok",
        embedding_provider=settings.embedding_provider,
        llm_model=settings.gemini_model,
        llm_configured=llm_configured(),
        documents=user_docs,
        chunks=chunks,
    )


@app.get("/", tags=["system"])
async def root() -> dict:
    return {
        "name": "PaperPilot API",
        "docs": "/docs",
        "health": "/api/health",
    }
