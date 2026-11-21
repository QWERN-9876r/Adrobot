"""Request-scoped sessions and service wiring."""
from fastapi import Request
from sqlalchemy.orm import Session
from adrobot.infrastructure.demo import Demo
from adrobot.services.container import Services


def get_services(request: Request):
    with Session(request.app.state.engine, expire_on_commit=False) as session:
        yield Services(session, request.app.state.tracker or Demo(session))
        session.commit()
