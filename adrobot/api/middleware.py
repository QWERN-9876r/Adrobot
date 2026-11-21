"""Local request policy and public error responses."""
import os
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from adrobot.domain.errors import Problem


def configure_middleware(application: FastAPI, port: int):
    hosts = {f"localhost:{port}", f"127.0.0.1:{port}"}
    origins = {f"http://{host}" for host in hosts}
    if os.getenv("ADROBOT_DEV") == "1":
        origins.update({"http://localhost:5173", "http://127.0.0.1:5173"})

    @application.middleware("http")
    async def local_requests(request: Request, call_next):
        response = None
        if request.headers.get("host") not in hosts:
            response = JSONResponse({"error": "Недопустимый хост."}, status_code=403)
        elif request.method in {"POST", "PUT"}:
            origin = request.headers.get("origin")
            content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            size = request.headers.get("content-length", "")
            if origin not in origins or content_type != "application/json":
                response = JSONResponse({"error": "Недопустимый источник запроса или тип содержимого."}, status_code=403)
            elif not size.isascii() or not size.isdecimal() or len(size) > 5 or not 0 < int(size) <= 65536:
                response = JSONResponse({"error": "Недопустимый размер запроса."}, status_code=400)

        if response is None:
            response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        return response

    @application.exception_handler(Problem)
    async def problem_response(_request: Request, error: Problem):
        return JSONResponse({"error": str(error), "code": error.code}, status_code=error.status)

    @application.exception_handler(RequestValidationError)
    async def validation_response(_request: Request, _error: RequestValidationError):
        return JSONResponse({"error": "Некорректные данные запроса."}, status_code=400)
