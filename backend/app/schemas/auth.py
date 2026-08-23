from datetime import datetime

from pydantic import BaseModel


class AthleteMe(BaseModel):
    """The logged-in athlete. Deliberately excludes tokens — those never leave the server."""

    athlete_id: int
    name: str
    created_at: datetime

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"athlete_id": 12345678, "name": "Bryan Alvin", "created_at": "2026-08-23T12:00:00Z"}
            ]
        }
    }


class LogoutResponse(BaseModel):
    status: str
