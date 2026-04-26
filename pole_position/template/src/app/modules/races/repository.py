from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from {{project_import_name}}.modules.races.model import Race, RaceStatus


class RaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[Race]:
        statement = select(Race).order_by(Race.scheduled_at.asc())
        return list(self.db.scalars(statement))

    def get(self, race_id: int) -> Race | None:
        return self.db.get(Race, race_id)

    def create(
        self,
        *,
        name: str,
        circuit: str,
        country: str,
        scheduled_at: datetime,
    ) -> Race:
        race = Race(
            name=name,
            circuit=circuit,
            country=country,
            scheduled_at=scheduled_at,
            status=RaceStatus.SCHEDULED.value,
        )
        self.db.add(race)
        self.db.commit()
        self.db.refresh(race)
        return race

    def update_status(self, race: Race, status: RaceStatus) -> Race:
        race.status = status.value
        self.db.add(race)
        self.db.commit()
        self.db.refresh(race)
        return race
