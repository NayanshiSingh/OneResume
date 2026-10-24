"""Ownership-aware editing of the signed-in user's profile.

Every lookup is scoped to the current user's profile, so items belonging to
other users behave exactly like items that do not exist.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.errors import InvalidRequestError, NotFoundError
from app.models.profile import (
    Achievement, Certification, Education, Experience, ExperienceBullet,
    ExternalProfile, PersonalInfo, Profile, Project, ProjectBullet, Skill,
)
from app.models.user import User
from app.schemas import ProfileImport

SectionModel = type[Education | Skill | Experience | Project | Certification | Achievement | ExternalProfile]

# Bullet model and its foreign key for each section that has bullets.
BULLETS = {
    Experience: (ExperienceBullet, "experience_id"),
    Project: (ProjectBullet, "project_id"),
}


def get_profile(db: Session, user: User) -> Profile:
    if user.profile is None:
        user.profile = Profile()
        db.commit()
    return user.profile


def _owned_item(db: Session, user: User, model: SectionModel, item_id: str):
    item = (
        db.query(model).join(Profile, model.profile_id == Profile.id)
        .filter(model.id == item_id, Profile.user_id == user.id).first()
    )
    if not item:
        raise NotFoundError(f"{model.__name__} not found")
    return item


def _owned_bullet(db: Session, user: User, parent_model: SectionModel, bullet_id: str):
    bullet_model, fk = BULLETS[parent_model]
    bullet = (
        db.query(bullet_model)
        .join(parent_model, getattr(bullet_model, fk) == parent_model.id)
        .join(Profile, parent_model.profile_id == Profile.id)
        .filter(bullet_model.id == bullet_id, Profile.user_id == user.id).first()
    )
    if not bullet:
        raise NotFoundError("Bullet not found")
    return bullet


def _next_position(db: Session, model, fk_column, parent_id: str) -> int:
    current = db.query(func.max(model.position)).filter(fk_column == parent_id).scalar()
    return 0 if current is None else current + 1


def _apply_order(items: list, ids: list[str]) -> None:
    by_id = {item.id: item for item in items}
    if len(ids) != len(set(ids)) or set(ids) != set(by_id):
        raise InvalidRequestError("ids must list every item exactly once")
    for position, item_id in enumerate(ids):
        by_id[item_id].position = position


def _invalidate_section_embedding(parent) -> None:
    if isinstance(parent, Experience):
        parent.experience_embedding = None


# ── Sections ─────────────────────────────────────────────────


def create_item(db: Session, user: User, model: SectionModel, fields: dict, bullets: list[str] = ()):
    profile = get_profile(db, user)
    item = model(
        profile_id=profile.id,
        position=_next_position(db, model, model.profile_id, profile.id),
        **fields,
    )
    if model in BULLETS:
        bullet_model, _ = BULLETS[model]
        item.bullets = [bullet_model(bullet_text=text, position=i) for i, text in enumerate(bullets)]
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, user: User, model: SectionModel, item_id: str, changes: dict):
    item = _owned_item(db, user, model, item_id)
    for name, value in changes.items():
        setattr(item, name, value)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, user: User, model: SectionModel, item_id: str) -> None:
    db.delete(_owned_item(db, user, model, item_id))
    db.commit()


def reorder_items(db: Session, user: User, model: SectionModel, ids: list[str]) -> None:
    profile = get_profile(db, user)
    _apply_order(db.query(model).filter(model.profile_id == profile.id).all(), ids)
    db.commit()


# ── Bullets ──────────────────────────────────────────────────


def add_bullet(db: Session, user: User, parent_model: SectionModel, parent_id: str, text: str):
    parent = _owned_item(db, user, parent_model, parent_id)
    bullet_model, fk = BULLETS[parent_model]
    bullet = bullet_model(
        bullet_text=text,
        position=_next_position(db, bullet_model, getattr(bullet_model, fk), parent.id),
        **{fk: parent.id},
    )
    db.add(bullet)
    _invalidate_section_embedding(parent)
    db.commit()
    db.refresh(bullet)
    return bullet


def update_bullet(db: Session, user: User, parent_model: SectionModel, bullet_id: str, text: str):
    bullet = _owned_bullet(db, user, parent_model, bullet_id)
    if bullet.bullet_text != text:
        bullet.bullet_text = text
        bullet.embedding = None
        _invalidate_section_embedding(getattr(bullet, "experience", None))
    db.commit()
    db.refresh(bullet)
    return bullet


def delete_bullet(db: Session, user: User, parent_model: SectionModel, bullet_id: str) -> None:
    bullet = _owned_bullet(db, user, parent_model, bullet_id)
    _invalidate_section_embedding(getattr(bullet, "experience", None))
    db.delete(bullet)
    db.commit()


def reorder_bullets(db: Session, user: User, parent_model: SectionModel, parent_id: str, ids: list[str]) -> None:
    parent = _owned_item(db, user, parent_model, parent_id)
    _apply_order(list(parent.bullets), ids)
    db.commit()


# ── Personal info ────────────────────────────────────────────


def upsert_personal_info(db: Session, user: User, fields: dict) -> PersonalInfo:
    profile = get_profile(db, user)
    if profile.personal_info is None:
        profile.personal_info = PersonalInfo(**fields)
    else:
        for name, value in fields.items():
            setattr(profile.personal_info, name, value)
    db.commit()
    db.refresh(profile.personal_info)
    return profile.personal_info


# ── Import ───────────────────────────────────────────────────

IMPORT_SECTIONS = {
    "education": Education, "skills": Skill, "experience": Experience, "projects": Project,
    "certifications": Certification, "achievements": Achievement, "external_profiles": ExternalProfile,
}


def apply_import(db: Session, user: User, data: ProfileImport) -> Profile:
    """Add reviewed imported sections to the profile; existing entries are kept."""
    if data.personal_info:
        upsert_personal_info(db, user, data.personal_info.model_dump())
    for name, model in IMPORT_SECTIONS.items():
        for item in getattr(data, name):
            fields = item.model_dump(exclude={"bullets"})
            bullets = [b.bullet_text for b in getattr(item, "bullets", [])]
            create_item(db, user, model, fields, bullets)
    return get_profile(db, user)
