"""User API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import UserCreate, UserOut
from app.repositories import UserRepository

router = APIRouter()


@router.post("/", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    return UserRepository.create(db, payload.username, payload.email)


@router.get("/", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return UserRepository.list_all(db)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db)):
    return UserRepository.get(db, user_id)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: str, db: Session = Depends(get_db)):
    UserRepository.delete(db, user_id)
