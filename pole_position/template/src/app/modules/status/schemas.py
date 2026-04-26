from datetime import datetime

from pydantic import BaseModel


class StatusResponse(BaseModel):
    status: str
    service: str
    environment: str
    version: str
    uptime_seconds: int
    timestamp: datetime
