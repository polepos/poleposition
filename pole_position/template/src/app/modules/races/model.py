from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from {{project_import_name}}.db.base import Base


class RaceStatus(StrEnum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class Race(Base):
    __tablename__ = "races"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    circuit: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default=RaceStatus.SCHEDULED.value)
