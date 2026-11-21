"""Compose request-scoped application services from shared dependencies."""
from sqlalchemy.orm import Session
from adrobot.domain.tracker import Tracker
from .catalog import CatalogService
from .creation import CampaignCreationService
from .streams import StreamService


class Services:
    def __init__(self, session: Session, api: Tracker):
        self.catalog = CatalogService(api)
        self.campaigns = CampaignCreationService(session, api)
        self.streams = StreamService(session, api)
