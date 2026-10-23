"""Shared FastAPI dependencies."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services import auth_service


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    user = auth_service.get_session_user(db, token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    return user
