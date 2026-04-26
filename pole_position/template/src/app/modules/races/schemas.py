from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from {{project_import_name}}.modules.races.model import RaceStatus


class RaceCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    circuit: str = Field(min_length=3, max_length=120)
    country: str = Field(min_length=2, max_length=80)
    scheduled_at: datetime


class RaceStatusUpdate(BaseModel):
    status: RaceStatus


class RaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    circuit: str
    country: str
    scheduled_at: datetime
    status: RaceStatus
