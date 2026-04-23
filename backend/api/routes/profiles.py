"""Rutas de perfiles de usuario (multi-perfil familiar)."""

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from backend.db.database import engine
from backend.models.user_profile import UserProfile, UserProfileCreate, UserProfileRead

router = APIRouter()


@router.get("/", response_model=list[UserProfileRead])
def list_profiles():
    with Session(engine) as session:
        profiles = session.exec(select(UserProfile).order_by(UserProfile.created_at)).all()
        if not profiles:
            # Seed default profile
            default = UserProfile(profile_id="default", name="Principal", color="#22c55e")
            session.add(default)
            session.commit()
            session.refresh(default)
            return [default]
        return profiles


@router.post("/", response_model=UserProfileRead)
def create_profile(body: UserProfileCreate):
    with Session(engine) as session:
        existing = session.exec(
            select(UserProfile).where(UserProfile.profile_id == body.profile_id)
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Perfil '{body.profile_id}' ya existe.")
        profile = UserProfile(**body.model_dump())
        session.add(profile)
        session.commit()
        session.refresh(profile)
        return profile


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: str):
    if profile_id == "default":
        raise HTTPException(status_code=400, detail="No puedes eliminar el perfil principal.")
    with Session(engine) as session:
        profile = session.exec(
            select(UserProfile).where(UserProfile.profile_id == profile_id)
        ).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Perfil no encontrado.")
        session.delete(profile)
        session.commit()
