"""FastAPI application composition root."""
from fastapi import FastAPI
from adrobot.logging import configure_logging
from .lifespan import lifespan
from .middleware import configure_middleware
from .routes import router as api_router
from .static import router as static_router


def create_app(port: int = 8000):
    configure_logging()
    application = FastAPI(title="Adrobot", lifespan=lifespan, docs_url=None, redoc_url=None)
    configure_middleware(application, port)
    application.include_router(api_router)
    application.include_router(static_router)
    return application
