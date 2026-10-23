"""Account routes: register, sign in and out, password reset, account deletion."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas import Credentials, PasswordResetConfirm, PasswordResetRequest, UserOut
from app.services import auth_service

router = APIRouter()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.SESSION_COOKIE_NAME, token,
        max_age=settings.SESSION_TTL_DAYS * 24 * 3600,
        httponly=True, secure=settings.COOKIE_SECURE, samesite="lax", path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: Credentials, response: Response, db: Session = Depends(get_db)):
    user = auth_service.register(db, payload.email, payload.password)
    _set_session_cookie(response, auth_service.create_session(db, user))
    return user


@router.post("/login", response_model=UserOut)
def login(payload: Credentials, response: Response, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    _set_session_cookie(response, auth_service.create_session(db, user))
    return user


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        auth_service.revoke_session(db, token)
    _clear_session_cookie(response)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/password-reset/request", status_code=202)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    auth_service.request_password_reset(db, payload.email)
    return {"detail": "If an account exists for that email, a reset link has been sent."}


@router.post("/password-reset/confirm", status_code=204)
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    if not auth_service.confirm_password_reset(db, payload.token, payload.new_password):
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")


@router.delete("/account", status_code=204)
def delete_account(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_service.delete_account(db, user)
    _clear_session_cookie(response)
