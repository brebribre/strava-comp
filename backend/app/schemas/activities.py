from datetime import datetime

from pydantic import BaseModel


class SyncResult(BaseModel):
    athlete_id: int
    since: datetime
    activities_saved: int
