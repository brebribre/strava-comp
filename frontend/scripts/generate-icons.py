"""Build every home-screen icon from one 1024px source.

Run with the backend's interpreter, which already has Pillow:

    backend/.venv/bin/python frontend/scripts/generate-icons.py

The source is `frontend/public/icon-1024.png`. Replace that file and re-run to change the
app's icon everywhere at once.
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "public" / "icon-1024.png"
PUBLIC = ROOT / "public"

# Android and some launchers crop a maskable icon to a circle of 80% diameter. The artwork
# is measured against that circle rather than guessed at: the white card's corners sit
# further from the centre than its edges do, and those are what get clipped.
SAFE_SCALE = 0.85


def background(image: Image.Image) -> tuple[int, int, int]:
    """Whatever colour the source pads itself with, so padding is invisible."""
    return image.getpixel((2, 2))


def full_bleed(source: Image.Image, size: int, path: Path) -> None:
    source.resize((size, size), Image.LANCZOS).save(path, "PNG")
    print(f"  {path.name}: {size}x{size}")


def maskable(source: Image.Image, size: int, path: Path) -> None:
    inner = int(size * SAFE_SCALE)
    canvas = Image.new("RGB", (size, size), background(source))
    offset = (size - inner) // 2
    canvas.paste(source.resize((inner, inner), Image.LANCZOS), (offset, offset))
    canvas.save(path, "PNG")
    print(f"  {path.name}: {size}x{size}, artwork at {int(SAFE_SCALE * 100)}%")


def main() -> None:
    source = Image.open(SOURCE).convert("RGB")
    full_bleed(source, 192, PUBLIC / "icon-192.png")
    full_bleed(source, 512, PUBLIC / "icon-512.png")
    # iOS rounds the corners itself and adds no padding of its own.
    full_bleed(source, 180, PUBLIC / "apple-touch-icon.png")
    full_bleed(source, 32, PUBLIC / "favicon.png")
    maskable(source, 512, PUBLIC / "icon-maskable-512.png")


if __name__ == "__main__":
    main()
