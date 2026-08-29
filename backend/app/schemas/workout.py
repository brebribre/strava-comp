from pydantic import BaseModel


class Exercise(BaseModel):
    """One exercise in a gym session, with its sets in the order they were done."""

    name: str
    # Free text straight from the logging app — "20 kg x 12", "10 reps", "1km - 7min".
    # Deliberately not parsed into numbers: every app writes these differently, and the
    # app that wrote them has already made them readable.
    sets: list[str]
