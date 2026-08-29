"""Workout checkpoint: reading a gym session's exercises out of its description.

Run with:  .venv/bin/python -m scripts.check_workout
"""

from sqlalchemy import text

from app.infra.db import engine
from app.services.workout import parse_exercises

HEVY = """Logged with hevyapp.com

Treadmill
Set 1: 1km - 7min

Overhead Press (Dumbbell)
Set 1: 20 kg x 12
Set 2: 20 kg x 12
Set 3: 20 kg x 11

Treadmill
Set 1: 1km - 6min
"""


def check(label: str, condition: bool, detail: str = "") -> None:
    assert condition, f"{label} FAILED {detail}"
    print(f"  ✓ {label}{(' — ' + detail) if detail else ''}")


def main() -> None:
    print("\nhevy descriptions")
    parsed = parse_exercises(HEVY)
    check("every block with sets becomes an exercise", len(parsed) == 3, str(len(parsed)))
    check("the logging app's own line is not an exercise",
          all("hevyapp" not in ex.name for ex in parsed))
    check("sets are kept in order",
          parsed[1].sets == ["20 kg x 12", "20 kg x 12", "20 kg x 11"], str(parsed[1].sets))
    check("a repeated exercise stays a separate block",
          [ex.name for ex in parsed] == ["Treadmill", "Overhead Press (Dumbbell)", "Treadmill"],
          "the order is the session")

    print("\nother shapes")
    check("bare set lines still count",
          parse_exercises("Pull Up\nSet 1\nSet 2")[0].sets == ["Set 1", "Set 2"])
    check("a dash instead of a colon is fine",
          parse_exercises("Pull Up\nSet 1 - 10 reps")[0].sets == ["10 reps"])
    check("blocks need no blank line between them",
          len(parse_exercises("Pull Up\nSet 1: 10 reps\nDips\nSet 1: 8 reps")) == 2)
    check("prose keeps its exercises",
          [ex.name for ex in parse_exercises("Felt strong today.\n\nSquat\nSet 1: 60 kg x 5")]
          == ["Squat"],
          "the sentence has no sets under it, the lift does")

    print("\nnothing to read")
    check("no description", parse_exercises(None) == [])
    check("empty description", parse_exercises("") == [])
    check("an ordinary note is not a workout",
          parse_exercises("Easy run along the river, legs felt good.") == [])
    check("a name with no sets is not an exercise", parse_exercises("Squat\n\nDeadlift") == [])

    print("\nagainst everything stored")
    with engine.connect() as connection:
        rows = connection.execute(text("""
            SELECT sport_type, raw_data->>'description' AS description
            FROM activities
            WHERE length(coalesce(raw_data->>'description', '')) > 0
        """)).all()

    parsed_rows = [(row.sport_type, parse_exercises(row.description)) for row in rows]
    with_exercises = [(sport, ex) for sport, ex in parsed_rows if ex]
    check("descriptions parse without raising", True, f"{len(rows)} descriptions")
    check("only strength sessions produce exercises",
          all(sport == "WeightTraining" for sport, _ in with_exercises),
          f"{len(with_exercises)} of {len(rows)} descriptions are workouts")
    check("every parsed exercise has at least one set",
          all(ex.sets for _, exercises in with_exercises for ex in exercises))

    print("\nWorkout checks OK")


if __name__ == "__main__":
    main()
