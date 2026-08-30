"""Server-side rendering of the activity share card.

The frontend draws the same card on a canvas for the in-app share sheet. This version
exists because notifications fire from a webhook, where there is no browser — so the
image has to be produced here. Keep the two in sync when restyling.
"""

import io
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.models import Activity, Athlete
from app.services.workout import parse_exercises

WIDTH = 1080
# The 4:5 portrait chat apps show without cropping is the *minimum*; a gym session with a
# dozen exercises grows the card rather than losing them.
MIN_HEIGHT = 1350
MAX_EXERCISES = 12
PAD = 84

# Always dark: the image lands in someone else's chat and should look deliberate.
BG = (10, 10, 10)
INK = (250, 250, 250)
INK_MUTED = (143, 143, 143)
LINE = (42, 42, 42)
RAISED = (24, 24, 24)

FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Inter.ttf"
MARK_PATH = Path(__file__).resolve().parent.parent / "assets" / "mark.png"

# Sports whose distance is meaningful; everything else reports time only.
FOOT_SPORTS = {"Run", "TrailRun", "VirtualRun", "Walk", "Hike"}
WHEEL_SPORTS = {"Ride", "VirtualRide", "GravelRide", "MountainBikeRide", "EBikeRide"}


@lru_cache(maxsize=16)
def _font(size: int, weight: int) -> ImageFont.FreeTypeFont:
    """Inter is a variable font, so one file covers every weight."""
    font = ImageFont.truetype(str(FONT_PATH), size)
    font.set_variation_by_axes([32, weight])
    return font


# ── Icon geometry, mirroring the frontend's useSportIcon ─────────────────────
_LINES: dict[str, list[list[tuple[float, float]]]] = {
    "Run": [
        [(29, 14), (24, 25)],
        [(27, 17), (35, 21)],
        [(27, 17), (18, 19)],
        [(24, 25), (28, 34), (33, 37)],
        [(24, 25), (17, 31), (12, 34)],
    ],
    "Ride": [
        [(11, 34), (21, 34), (28, 21), (33, 21)],
        [(21, 34), (29, 18)],
        [(37, 34), (31, 21)],
    ],
    "Swim": [
        [(9, 25), (23, 21), (35, 24)],
        [(23, 21), (33, 13)],
        [(5, 36), (11, 33), (17, 37), (23, 33), (29, 37), (35, 33), (41, 37)],
    ],
    "Tennis": [[(26, 27), (36, 39)]],
    "WeightTraining": [[(15, 24), (33, 24)], [(4, 20), (4, 28)], [(44, 20), (44, 28)]],
    "Walk": [[(28, 15), (25, 25)], [(25, 25), (29, 34)], [(25, 25), (19, 33)], [(26, 19), (32, 22)]],
}

_CIRCLES: dict[str, list[tuple[float, float, float]]] = {
    "Run": [(30, 9, 4)],
    "Ride": [(11, 34, 7.5), (37, 34, 7.5), (31, 10, 3.5)],
    "Swim": [(17, 15, 4)],
    "Tennis": [(38, 16, 3.5), (20, 18, 11)],
    "WeightTraining": [],
    "Walk": [(29, 10, 4)],
}

_RECTS: dict[str, list[tuple[float, float, float, float]]] = {
    "WeightTraining": [(8, 17, 14, 31), (34, 17, 40, 31)],
}


def resolve_sport(sport_type: str | None) -> str:
    if not sport_type:
        return "Run"
    if sport_type in _LINES:
        return sport_type
    lowered = sport_type.lower()
    if "run" in lowered:
        return "Run"
    if any(word in lowered for word in ("ride", "bike", "cycl")):
        return "Ride"
    if "swim" in lowered:
        return "Swim"
    if any(word in lowered for word in ("tennis", "padel", "squash", "badminton")):
        return "Tennis"
    if any(word in lowered for word in ("weight", "workout", "crossfit")):
        return "WeightTraining"
    if "walk" in lowered or "hike" in lowered:
        return "Walk"
    return "Run"


def _draw_icon(draw: ImageDraw.ImageDraw, sport_type: str | None, x: int, y: int, size: int) -> None:
    key = resolve_sport(sport_type)
    scale = size / 48
    width = max(int(round(2.6 * scale)), 2)

    def point(px: float, py: float) -> tuple[float, float]:
        return (x + px * scale, y + py * scale)

    for polyline in _LINES.get(key, []):
        draw.line([point(*p) for p in polyline], fill=INK, width=width, joint="curve")
    for cx, cy, r in _CIRCLES.get(key, []):
        left, top = point(cx - r, cy - r)
        right, bottom = point(cx + r, cy + r)
        draw.ellipse([left, top, right, bottom], outline=INK, width=width)
    for rx, ry, rx2, ry2 in _RECTS.get(key, []):
        draw.rounded_rectangle(
            [*point(rx, ry), *point(rx2, ry2)], radius=int(2 * scale), outline=INK, width=width
        )


def _format_duration(seconds: int) -> str:
    hours, minutes = divmod(round(seconds / 60), 60)
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"


def _pace_or_speed(sport_type: str | None, metres: float, seconds: int) -> tuple[str, str] | None:
    if not sport_type or metres < 100 or seconds <= 0:
        return None
    if sport_type in FOOT_SPORTS:
        per_km = seconds / (metres / 1000)
        return "Pace", f"{int(per_km // 60)}:{round(per_km % 60):02d} /km"
    if sport_type in WHEEL_SPORTS:
        return "Speed", f"{metres / 1000 / seconds * 3600:.1f} km/h"
    return None


def _stats(activity: Activity) -> list[tuple[str, str]]:
    stats: list[tuple[str, str]] = []
    if (activity.distance or 0) > 0:
        stats.append(("Distance", f"{(activity.distance or 0) / 1000:.1f} km"))
    stats.append(("Moving time", _format_duration(activity.moving_time or 0)))
    rate = _pace_or_speed(activity.sport_type, activity.distance or 0, activity.moving_time or 0)
    if rate:
        stats.append(rate)
    if (activity.total_elevation_gain or 0) > 0:
        stats.append(("Elevation", f"{round(activity.total_elevation_gain or 0)} m"))
    if activity.average_heartrate is not None:
        stats.append(("Avg HR", f"{round(activity.average_heartrate)} bpm"))
    if activity.max_heartrate is not None:
        stats.append(("Max HR", f"{round(activity.max_heartrate)} bpm"))
    return stats


def _sport_label(sport_type: str | None) -> str:
    """"WeightTraining" → "WEIGHT TRAINING". Strava's PascalCase is not a display name."""
    if not sport_type:
        return "ACTIVITY"
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", sport_type).upper()


def _initials(name: str) -> str:
    return "".join(part[0].upper() for part in name.split()[:2]) or "?"


def _wordmark(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """BRUDERBANDE, tracked out to match AppLogo. Drawn glyph by glyph for the tracking."""
    font = _font(size, 800)
    tracking = size * 0.18
    cursor = float(x)
    for char in "BRUDERBANDE":
        draw.text((cursor, y), char, font=font, fill=INK)
        cursor += font.getlength(char) + tracking


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if font.getlength(candidate) > max_width and line:
            lines.append(line)
            line = word
            if len(lines) == max_lines:
                return lines
        else:
            line = candidate
    if line and len(lines) < max_lines:
        lines.append(line)
    return lines


def _paste_mark(image: Image.Image, x: int, y: int, size: int) -> bool:
    """The app icon, rounded like it is on a home screen. False if the file is missing."""
    if not MARK_PATH.exists():
        return False

    mark = Image.open(MARK_PATH).convert("RGB").resize((size, size), Image.LANCZOS)
    rounded = Image.new("L", (size, size), 0)
    ImageDraw.Draw(rounded).rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 5, fill=255)
    image.paste(mark, (x, y), rounded)
    return True


def _ellipsize(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    if font.getlength(text) <= max_width:
        return text
    cut = text
    while len(cut) > 1 and font.getlength(f"{cut}…") > max_width:
        cut = cut[:-1]
    return f"{cut}…"


def render_activity_card(activity: Activity, athlete: Athlete) -> bytes:
    """The activity as a PNG, ready to upload to Telegram."""
    # Measured before anything is drawn, because the canvas has to be created at its final
    # height and the exercise list is what varies.
    title_font = _font(66, 700)
    title_lines = _wrap(activity.name or "Untitled activity", title_font, WIDTH - PAD * 2, 2)
    stats = _stats(activity)[:6]
    stat_rows = -(-len(stats) // 2)
    all_exercises = parse_exercises((activity.raw_data or {}).get("description"))
    exercises = all_exercises[:MAX_EXERCISES]
    hidden = len(all_exercises) - len(exercises)

    icon_top = PAD + 210
    title_bottom = icon_top + 226 + (len(title_lines) - 1) * 78
    grid_top = title_bottom + 130
    grid_bottom = grid_top + stat_rows * 150
    exercises_top = grid_bottom + 20
    exercises_height = (70 + len(exercises) * 96 + (52 if hidden else 0)) if exercises else 0
    content_bottom = exercises_top + exercises_height + 40
    height = max(MIN_HEIGHT, content_bottom + 150)
    # On a short card the footer sits at the bottom rather than wherever the content ran
    # out, which would leave it stranded in the middle of the picture.
    footer_top = height - 150

    image = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(image)

    # ── Profile row ──
    avatar = 96
    draw.rounded_rectangle([PAD, PAD, PAD + avatar, PAD + avatar], radius=12, fill=RAISED, outline=LINE, width=2)
    initials_font = _font(34, 600)
    initials = _initials(athlete.name)
    draw.text(
        (PAD + avatar / 2 - initials_font.getlength(initials) / 2, PAD + avatar / 2 - 22),
        initials,
        font=initials_font,
        fill=INK_MUTED,
    )

    draw.text((PAD + avatar + 28, PAD + 8), athlete.name, font=_font(40, 700), fill=INK)
    when: datetime | None = activity.start_date
    if when:
        draw.text(
            (PAD + avatar + 28, PAD + 58),
            when.strftime("%a, %d %b, %H:%M"),
            font=_font(30, 400),
            fill=INK_MUTED,
        )

    # ── Icon + title ──
    icon_top = PAD + 210
    _draw_icon(draw, activity.sport_type, PAD, icon_top, 130)

    draw.text(
        (PAD, icon_top + 176),
        _sport_label(activity.sport_type),
        font=_font(30, 500),
        fill=INK_MUTED,
    )

    for index, line in enumerate(title_lines):
        draw.text((PAD, icon_top + 226 + index * 78), line, font=title_font, fill=INK)

    # ── Stats grid ──
    label_font = _font(28, 500)
    value_font = _font(58, 700)
    column = (WIDTH - PAD * 2) // 2
    for index, (label, value) in enumerate(stats):
        x = PAD + (index % 2) * column
        y = grid_top + (index // 2) * 150
        draw.text((x, y), label.upper(), font=label_font, fill=INK_MUTED)
        draw.text((x, y + 40), value, font=value_font, fill=INK)

    # ── The session itself, when it was a logged gym workout ──
    if exercises:
        draw.line([PAD, exercises_top, WIDTH - PAD, exercises_top], fill=LINE, width=2)
        draw.text(
            (PAD, exercises_top + 30),
            f"{len(all_exercises)} EXERCISE{'' if len(all_exercises) == 1 else 'S'}",
            font=_font(28, 500),
            fill=INK_MUTED,
        )

        name_font = _font(40, 600)
        sets_font = _font(32, 400)
        for index, exercise in enumerate(exercises):
            y = exercises_top + 70 + index * 96
            draw.text(
                (PAD, y + 10),
                _ellipsize(exercise.name, name_font, WIDTH - PAD * 2),
                font=name_font,
                fill=INK,
            )
            draw.text(
                (PAD, y + 58),
                _ellipsize("  ·  ".join(exercise.sets), sets_font, WIDTH - PAD * 2),
                font=sets_font,
                fill=INK_MUTED,
            )

        if hidden:
            draw.text(
                (PAD, exercises_top + 70 + len(exercises) * 96 + 10),
                f"+{hidden} more",
                font=_font(30, 500),
                fill=INK_MUTED,
            )

    # ── Footer: the mark, then the wordmark ──
    draw.line([PAD, footer_top, WIDTH - PAD, footer_top], fill=LINE, width=2)
    mark_size = 64
    mark_top = footer_top + 40
    wordmark_x = PAD + mark_size + 24 if _paste_mark(image, PAD, mark_top, mark_size) else PAD
    _wordmark(draw, wordmark_x, mark_top + 14, 30)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
