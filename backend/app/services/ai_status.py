"""Which AI providers are configured. Features without one run in labelled basic mode."""

from app.config import settings

AI = "ai"
BASIC = "basic"
OPENAI_COMPATIBLE = "openai_compatible"


def llm_available() -> bool:
    key = settings.LLM_API_KEY if settings.LLM_PROVIDER == OPENAI_COMPATIBLE else settings.GEMINI_API_KEY
    return bool(key)


def llm_provider_name() -> str:
    return settings.LLM_PROVIDER_NAME if settings.LLM_PROVIDER == OPENAI_COMPATIBLE else "Google Gemini"


def embeddings_available() -> bool:
    return bool(settings.PINECONE_API_KEY)


def status() -> dict:
    return {"llm": llm_available(), "llm_provider": llm_provider_name(), "embeddings": embeddings_available()}
