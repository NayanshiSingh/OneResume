"""Accounts: password hashing, sessions, password reset, and account deletion.

Session and reset tokens are random values given to the browser or user;
only their SHA-256 hashes are stored, so a database leak does not expose
usable tokens.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import ConflictError
from app.models.profile import Profile
from app.models.user import PasswordResetToken, User, UserSession
from app.services import mailer
from app.services.storage import get_storage

_hasher = PasswordHash.recommended()
# Verified against when the email is unknown, so login takes similar time either way.
_DUMMY_HASH = _hasher.hash("timing-equaliser")


def utcnow() -> datetime:
    """Naive UTC, matching how DateTime columns are stored."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _normalise_email(email: str) -> str:
    return email.strip().lower()


def register(db: Session, email: str, password: str) -> User:
    email = _normalise_email(email)
    if db.query(User).filter(User.email == email).first():
        raise ConflictError("An account with this email already exists")
    user = User(email=email, password_hash=_hasher.hash(password))
    user.profile = Profile()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == _normalise_email(email)).first()
    if not user:
        _hasher.verify(password, _DUMMY_HASH)
        return None
    return user if _hasher.verify(password, user.password_hash) else None


def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(UserSession(
        token_hash=_token_hash(token), user_id=user.id,
        expires_at=utcnow() + timedelta(days=settings.SESSION_TTL_DAYS),
    ))
    db.commit()
    return token


def get_session_user(db: Session, token: str) -> User | None:
    session = db.get(UserSession, _token_hash(token))
    if not session:
        return None
    if session.expires_at <= utcnow():
        db.delete(session)
        db.commit()
        return None
    return session.user


def revoke_session(db: Session, token: str) -> None:
    db.query(UserSession).filter(UserSession.token_hash == _token_hash(token)).delete()
    db.commit()


def request_password_reset(db: Session, email: str) -> None:
    """Send a reset link if the account exists. Callers must not reveal which."""
    user = db.query(User).filter(User.email == _normalise_email(email)).first()
    if not user:
        return
    token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        token_hash=_token_hash(token), user_id=user.id,
        expires_at=utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES),
    ))
    db.commit()
    link = f"{settings.APP_BASE_URL}/reset-password?{urlencode({'token': token})}"
    mailer.send_password_reset(user.email, link)


def confirm_password_reset(db: Session, token: str, new_password: str) -> bool:
    reset = db.get(PasswordResetToken, _token_hash(token))
    if not reset or reset.used_at or reset.expires_at <= utcnow():
        return False
    reset.used_at = utcnow()
    reset.user.password_hash = _hasher.hash(new_password)
    # Sign out everywhere: whoever triggered the reset may not be the only session holder.
    db.query(UserSession).filter(UserSession.user_id == reset.user_id).delete()
    db.commit()
    return True


def delete_account(db: Session, user: User) -> None:
    get_storage().delete_prefix(f"users/{user.id}")
    db.delete(user)
    db.commit()
