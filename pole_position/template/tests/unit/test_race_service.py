from datetime import datetime, timedelta, timezone

import pytest

from {{project_import_name}}.domain.exceptions import DomainError
from {{project_import_name}}.modules.races.schemas import RaceCreate
from {{project_import_name}}.modules.races.service import RaceService


def test_create_race_rejects_past_schedule() -> None:
    payload = RaceCreate(
        name="Retro Grand Prix",
        circuit="Old Circuit",
        country="Italy",
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=1),
    )

    with pytest.raises(DomainError):
        RaceService(db=None).create_race(payload)  # type: ignore[arg-type]
