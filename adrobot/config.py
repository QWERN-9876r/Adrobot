"""Project paths shared by runtime and migrations."""
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_BUILD = ROOT / "frontend" / "dist"


def load_environment(path: Path = ROOT / ".env") -> None:
    # Keep process environment overrides and preserve literal values from .env.
    load_dotenv(path, override=False, interpolate=False, encoding="utf-8")


load_environment()
