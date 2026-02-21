"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'oneresume.db'}"

    # ── Gemini LLM ────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # ── Embeddings ────────────────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # ── Resume constraints ────────────────────────────────────
    MAX_EXPERIENCE_SECTIONS: int = 3
    MAX_PROJECT_SECTIONS: int = 3
    MAX_BULLETS_PER_SECTION: int = 4
    MAX_SKILLS: int = 12

    # ── File storage ──────────────────────────────────────────
    OUTPUT_DIR: str = str(BASE_DIR / "output")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
