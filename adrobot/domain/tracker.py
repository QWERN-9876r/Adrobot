"""Port implemented by the live and demo tracker adapters."""
from typing import Protocol

OPTIONS = {"offers": "/offers", "domains": "/domains",
           "groups": "/groups?type=campaigns", "sources": "/traffic_sources"}


class Tracker(Protocol):
    mode: str
    identity: str

    def call(self, path: str, method: str = "GET", body=None): ...
