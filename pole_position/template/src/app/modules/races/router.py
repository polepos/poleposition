from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from {{project_import_name}}.api.deps import db_session
from {{project_import_name}}.modules.races.model import RaceStatus
from {{project_import_name}}.modules.races.schemas import (
    RaceCreate,
    RaceRead,
    RaceStatusUpdate,
)
from {{project_import_name}}.modules.races.service import RaceService


router = APIRouter()


@router.get("/", response_model=list[RaceRead])
def list_races(db: Session = Depends(db_session)) -> list[RaceRead]:
    return RaceService(db).list_races()


@router.get("/{race_id}", response_model=RaceRead)
def get_race(race_id: int, db: Session = Depends(db_session)) -> RaceRead:
    return RaceService(db).get_race(race_id)


@router.post("/", response_model=RaceRead, status_code=status.HTTP_201_CREATED)
def create_race(payload: RaceCreate, db: Session = Depends(db_session)) -> RaceRead:
    return RaceService(db).create_race(payload)


@router.patch("/{race_id}/status", response_model=RaceRead)
def update_race_status(
    race_id: int,
    payload: RaceStatusUpdate,
    db: Session = Depends(db_session),
) -> RaceRead:
    return RaceService(db).update_race_status(race_id, RaceStatus(payload.status))
