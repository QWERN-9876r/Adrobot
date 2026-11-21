"""Project paths shared by runtime and migrations."""
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_BUILD = ROOT / "frontend" / "dist"


def load_environment(path: Path = ROOT / ".env") -> None:
    # Environment overrides the file. Disable interpolation so passwords
    # containing dollar signs are preserved literally.
    load_dotenv(path, override=False, interpolate=False, encoding="utf-8")


load_environment()
