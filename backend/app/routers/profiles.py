"""Routes for the signed-in user's profile and its sections."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.profile import (
    Achievement, Certification, Education, Experience, ExternalProfile, Project, Skill,
)
from app.models.user import User
from app.schemas import (
    AchievementCreate, AchievementOut, AchievementUpdate,
    BulletCreate, BulletOut,
    CertificationCreate, CertificationOut, CertificationUpdate,
    EducationCreate, EducationOut, EducationUpdate,
    ExperienceCreate, ExperienceOut, ExperienceUpdate,
    ExternalProfileCreate, ExternalProfileOut, ExternalProfileUpdate,
    PersonalInfoCreate, PersonalInfoOut, ProfileOut,
    ProjectCreate, ProjectOut, ProjectUpdate,
    ReorderRequest,
    SkillCreate, SkillOut, SkillUpdate,
)
from app.services import profile_service

router = APIRouter()


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return profile_service.get_profile(db, user)


@router.put("/personal-info", response_model=PersonalInfoOut)
def upsert_personal_info(
    payload: PersonalInfoCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    return profile_service.upsert_personal_info(db, user, payload.model_dump())


def _add_section_routes(
    path: str, model, create_schema: type[BaseModel], update_schema, out_schema,
) -> None:
    """Register create, update, delete, and reorder routes for one profile section."""

    def create(payload: create_schema, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        fields = payload.model_dump(exclude={"bullets"})
        bullets = [b.bullet_text for b in getattr(payload, "bullets", [])]
        return profile_service.create_item(db, user, model, fields, bullets)

    def update(item_id: str, payload: update_schema, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        return profile_service.update_item(db, user, model, item_id, payload.changes())

    def delete(item_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        profile_service.delete_item(db, user, model, item_id)

    def reorder(payload: ReorderRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        profile_service.reorder_items(db, user, model, payload.ids)

    name = path.replace("-", "_")
    router.add_api_route(f"/{path}", create, methods=["POST"], response_model=out_schema, status_code=201, name=f"create_{name}")
    router.add_api_route(f"/{path}/order", reorder, methods=["PUT"], status_code=204, name=f"reorder_{name}")
    router.add_api_route(f"/{path}/{{item_id}}", update, methods=["PATCH"], response_model=out_schema, name=f"update_{name}")
    router.add_api_route(f"/{path}/{{item_id}}", delete, methods=["DELETE"], status_code=204, name=f"delete_{name}")


def _add_bullet_routes(path: str, parent_model) -> None:
    """Register bullet routes nested under experience or project entries."""

    def add(item_id: str, payload: BulletCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        return profile_service.add_bullet(db, user, parent_model, item_id, payload.bullet_text)

    def reorder(item_id: str, payload: ReorderRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        profile_service.reorder_bullets(db, user, parent_model, item_id, payload.ids)

    def update(bullet_id: str, payload: BulletCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        return profile_service.update_bullet(db, user, parent_model, bullet_id, payload.bullet_text)

    def delete(bullet_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        profile_service.delete_bullet(db, user, parent_model, bullet_id)

    name = path.replace("-", "_")
    router.add_api_route(f"/{path}/{{item_id}}/bullets", add, methods=["POST"], response_model=BulletOut, status_code=201, name=f"add_{name}_bullet")
    router.add_api_route(f"/{path}/{{item_id}}/bullets/order", reorder, methods=["PUT"], status_code=204, name=f"reorder_{name}_bullets")
    router.add_api_route(f"/{path}/bullets/{{bullet_id}}", update, methods=["PATCH"], response_model=BulletOut, name=f"update_{name}_bullet")
    router.add_api_route(f"/{path}/bullets/{{bullet_id}}", delete, methods=["DELETE"], status_code=204, name=f"delete_{name}_bullet")


# Bullet routes first so "/experience/bullets/{id}" is not captured by "/experience/{item_id}".
_add_bullet_routes("experience", Experience)
_add_bullet_routes("projects", Project)
_add_section_routes("education", Education, EducationCreate, EducationUpdate, EducationOut)
_add_section_routes("skills", Skill, SkillCreate, SkillUpdate, SkillOut)
_add_section_routes("experience", Experience, ExperienceCreate, ExperienceUpdate, ExperienceOut)
_add_section_routes("projects", Project, ProjectCreate, ProjectUpdate, ProjectOut)
_add_section_routes("certifications", Certification, CertificationCreate, CertificationUpdate, CertificationOut)
_add_section_routes("achievements", Achievement, AchievementCreate, AchievementUpdate, AchievementOut)
_add_section_routes("external-profiles", ExternalProfile, ExternalProfileCreate, ExternalProfileUpdate, ExternalProfileOut)
