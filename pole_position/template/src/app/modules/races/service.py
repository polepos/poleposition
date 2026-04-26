from datetime import datetime, timezone

from sqlalchemy.orm import Session

from {{project_import_name}}.domain.exceptions import DomainError, NotFoundError
from {{project_import_name}}.modules.races.model import Race, RaceStatus
from {{project_import_name}}.modules.races.repository import RaceRepository
from {{project_import_name}}.modules.races.schemas import RaceCreate


class RaceService:
    def __init__(self, db: Session) -> None:
        self.repository = RaceRepository(db)

    def list_races(self) -> list[Race]:
        return self.repository.list()

    def get_race(self, race_id: int) -> Race:
        race = self.repository.get(race_id)
        if race is None:
            raise NotFoundError(f"Race {race_id} was not found.")
        return race

    def create_race(self, payload: RaceCreate) -> Race:
        scheduled_at = payload.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

        if scheduled_at < datetime.now(timezone.utc):
            raise DomainError("Race schedule must be in the future.")

        return self.repository.create(
            name=payload.name,
            circuit=payload.circuit,
            country=payload.country,
            scheduled_at=scheduled_at,
        )

    def update_race_status(self, race_id: int, status: RaceStatus) -> Race:
        race = self.get_race(race_id)
        current = RaceStatus(race.status)

        if current in {RaceStatus.FINISHED, RaceStatus.CANCELLED}:
            raise DomainError("Completed races cannot change status.")

        if current == status:
            raise DomainError("Race is already in the requested status.")

        return self.repository.update_status(race, status)
