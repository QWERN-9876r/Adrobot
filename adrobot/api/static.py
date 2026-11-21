"""Serve the compiled UI and explicitly allowed static files."""
import re
from fastapi import APIRouter
from fastapi.responses import FileResponse, PlainTextResponse
from adrobot.config import FRONTEND_BUILD
from adrobot.domain.errors import Problem

router = APIRouter()
ASSET_TYPES = {".css": "text/css", ".js": "text/javascript", ".png": "image/png"}

@router.get("/", include_in_schema=False)
def index():
    path = FRONTEND_BUILD / "index.html"
    if path.is_file():
        return FileResponse(path, media_type="text/html")
    return PlainTextResponse("Соберите интерфейс командой npm --prefix frontend run build.", status_code=503)

@router.get("/assets/{filename}", include_in_schema=False)
def asset(filename: str):
    if re.fullmatch(r"[A-Za-z0-9_-]+\.(css|js)", filename):
        path = FRONTEND_BUILD / "assets" / filename
        if path.is_file():
            return FileResponse(path, media_type=ASSET_TYPES[path.suffix])
    raise Problem("Страница не найдена.", 404)


@router.get("/brand/{filename}", include_in_schema=False)
def brand_asset(filename: str):
    if filename in {"adrobot-icon.png", "favicon-32.png"}:
        path = FRONTEND_BUILD / "brand" / filename
        if path.is_file():
            return FileResponse(path, media_type="image/png")
    raise Problem("Изображение не найдено.", 404)
