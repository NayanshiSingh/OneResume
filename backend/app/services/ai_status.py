"""Which AI providers are configured. Features without one run in labelled basic mode."""

from app.config import settings

AI = "ai"
BASIC = "basic"


def llm_available() -> bool:
    return bool(settings.GEMINI_API_KEY)


def embeddings_available() -> bool:
    return bool(settings.PINECONE_API_KEY)


def status() -> dict[str, bool]:
    return {"llm": llm_available(), "embeddings": embeddings_available()}
