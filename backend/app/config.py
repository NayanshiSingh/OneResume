"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'oneresume.db'}"

    # ── Gemini LLM ────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3-flash-preview"

    # ── Pinecone Embeddings ──────────────────────────────────
    PINECONE_API_KEY: str = ""
    EMBEDDING_MODEL: str = "multilingual-e5-large"
    EMBEDDING_DIM: int = 1024

    # ── Resume constraints ────────────────────────────────────
    MAX_EXPERIENCE_SECTIONS: int = 3
    MAX_PROJECT_SECTIONS: int = 3
    MAX_BULLETS_PER_SECTION: int = 5
    BULLETS_PER_PAGE: int = 14  # experience + project bullets that fit one page
    MAX_SKILLS: int = 12

    # ── Accounts and sessions ─────────────────────────────────
    SESSION_COOKIE_NAME: str = "oneresume_session"
    SESSION_TTL_DAYS: int = 14
    COOKIE_SECURE: bool = False
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    APP_BASE_URL: str = "http://localhost:3000"
    PASSWORD_RESET_TTL_MINUTES: int = 30

    # ── Limits (rolling 24 hours per user unless noted) ───────
    DAILY_JD_ANALYSES: int = 30
    DAILY_RESUME_IMPORTS: int = 10
    DAILY_DRAFTS: int = 30
    LOGIN_FAILURE_LIMIT: int = 10  # per email, within LOGIN_FAILURE_WINDOW_MINUTES
    LOGIN_FAILURE_WINDOW_MINUTES: int = 15
    RESET_REQUESTS_PER_HOUR: int = 3  # per email; extra requests send nothing

    # ── Private file storage ──────────────────────────────────
    STORAGE_DIR: str = str(BASE_DIR / "storage")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
