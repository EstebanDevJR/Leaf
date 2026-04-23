from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from backend.db.database import engine
from backend.models.savings_goal import (
    SavingsGoal,
    SavingsGoalCreate,
    SavingsGoalRead,
    SavingsGoalUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[SavingsGoalRead])
def list_goals(profile_id: str = "default", include_completed: bool = False):
    with Session(engine) as session:
        q = select(SavingsGoal).where(SavingsGoal.profile_id == profile_id)
        if not include_completed:
            q = q.where(SavingsGoal.completed_at.is_(None))
        return session.exec(q.order_by(SavingsGoal.created_at.desc())).all()


@router.post("/", response_model=SavingsGoalRead)
def create_goal(body: SavingsGoalCreate):
    with Session(engine) as session:
        goal = SavingsGoal(**body.model_dump())
        session.add(goal)
        session.commit()
        session.refresh(goal)
        return goal


@router.patch("/{goal_id}", response_model=SavingsGoalRead)
def update_goal(goal_id: int, body: SavingsGoalUpdate):
    with Session(engine) as session:
        goal = session.get(SavingsGoal, goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Meta no encontrada")
        data = body.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(goal, k, v)
        goal.updated_at = datetime.utcnow()
        if goal.current_amount >= goal.target_amount and not goal.completed_at:
            goal.completed_at = datetime.utcnow()
        session.add(goal)
        session.commit()
        session.refresh(goal)
        return goal


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: int):
    with Session(engine) as session:
        goal = session.get(SavingsGoal, goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Meta no encontrada")
        session.delete(goal)
        session.commit()
