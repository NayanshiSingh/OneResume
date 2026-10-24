"""System information for the frontend."""

from fastapi import APIRouter

from app.schemas import AIStatus
from app.services import ai_status

router = APIRouter()


@router.get("/ai-status", response_model=AIStatus)
def get_ai_status():
    """Which AI providers are configured; features without one run in basic mode."""
    return ai_status.status()
