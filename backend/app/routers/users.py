"""User API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.hash import bcrypt

from app.database import get_db
from app.schemas import UserCreate, UserOut, LoginOrRegister
from app.repositories import UserRepository, ProfileRepository
from app.models.user import User as UserModel

router = APIRouter()


@router.post("/login-or-register", response_model=UserOut)
def login_or_register(payload: LoginOrRegister, db: Session = Depends(get_db)):
    """Authenticate an existing user or register a new one.

    - If email exists → verify password → return user
    - If email doesn't exist → create user + profile → return user
    """
    existing = UserRepository.get_by_email(db, payload.email)

    if existing:
        # Verify password
        if not bcrypt.verify(payload.password, existing.password_hash):
            raise HTTPException(status_code=401, detail="Invalid password")
        return existing
    else:
        # Register new user — derive username from email
        username = payload.email.split("@")[0]
        # Ensure username is unique
        base_username = username
        counter = 1
        while db.query(UserModel).filter(UserModel.username == username).first():
            username = f"{base_username}_{counter}"
            counter += 1

        password_hash = bcrypt.hash(payload.password)
        user = UserRepository.create(db, username, payload.email, password_hash)
        # Auto-create an empty profile for the new user
        ProfileRepository.create(db, user.id)
        return user


@router.post("/", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    password_hash = bcrypt.hash(payload.password)
    return UserRepository.create(db, payload.username, payload.email, password_hash)


@router.get("/", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return UserRepository.list_all(db)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db)):
    return UserRepository.get(db, user_id)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: str, db: Session = Depends(get_db)):
    UserRepository.delete(db, user_id)
