"""Reading the exercise breakdown of a gym session out of its description.

Strava's API has no structured strength data: the detailed activity for a WeightTraining
session carries sixty-odd fields and not one of them is an exercise, a set or a rep. What
it does carry is the description, and the apps people log lifts in — Hevy, Strong and the
rest — write the whole session into it as text:

    Logged with hevyapp.com

    Overhead Press (Dumbbell)
    Set 1: 20 kg x 12
    Set 2: 20 kg x 12

    Treadmill
    Set 1: 1km - 7min

So the sequence is already in the data we store; it just arrives as prose. Everything below
is a parser for that, deliberately conservative: anything it does not recognise is left
alone and the description still shows as written.
"""

import re

from app.schemas.workout import Exercise

# "Set 1: 20 kg x 12", "Set 2 - 10 reps", "set 3. 1km - 7min".
_SET_LINE = re.compile(r"^set\s*(\d+)\s*[:.\-]?\s*(?P<detail>.*)$", re.IGNORECASE)

# Lines the logging app adds about itself rather than about the training.
_PREAMBLE = re.compile(r"logged with|powered by|via\s+\w+app", re.IGNORECASE)


def parse_exercises(description: str | None) -> list[Exercise]:
    """Pull the exercise sequence out of a description, or return nothing.

    Order and repeats are preserved: a treadmill block between two lifts is how the session
    actually went, and collapsing the three treadmill blocks into one would rewrite it.
    """
    if not description:
        return []

    exercises: list[Exercise] = []
    name: str | None = None
    sets: list[str] = []

    def flush() -> None:
        # An exercise is only an exercise once it has a set under it. This is what keeps
        # "Logged with hevyapp.com" and ordinary prose out of the list.
        if name and sets:
            exercises.append(Exercise(name=name, sets=list(sets)))

    for raw_line in description.splitlines():
        line = raw_line.strip()

        if not line:
            flush()
            name, sets = None, []
            continue

        match = _SET_LINE.match(line)
        if match:
            detail = match.group("detail").strip()
            # A set with no detail is still a set — bodyweight apps write bare "Set 1".
            sets.append(detail or f"Set {match.group(1)}")
            continue

        # A non-set line starts a new exercise, so the previous one ends here even without
        # a blank line between them.
        flush()
        name, sets = (None if _PREAMBLE.search(line) else line), []

    flush()
    return exercises
