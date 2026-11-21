"""HTTP endpoints delegate to application services."""
from fastapi import APIRouter, Depends
from adrobot.domain.countries import COUNTRY_CODES
from adrobot.services.container import Services
from .dependencies import get_services
from .schemas import CampaignInput, StreamDraft, CampaignResponse, CatalogResponse, StreamResponse

router = APIRouter(prefix="/api")


@router.get("/catalog", response_model=CatalogResponse)
def catalog(services: Services = Depends(get_services)):
    return {"mode": services.catalog.mode, "countries": sorted(COUNTRY_CODES), **services.catalog.load()}


@router.get("/campaigns", response_model=list[CampaignResponse])
def campaigns(services: Services = Depends(get_services)):
    return services.catalog.campaigns()


@router.get("/campaigns/{campaign_id}/streams", response_model=list[StreamResponse])
def streams(campaign_id: int, services: Services = Depends(get_services)):
    return services.streams.list(campaign_id)


@router.post("/campaigns", response_model=CampaignResponse)
def create_campaign(data: CampaignInput, services: Services = Depends(get_services)):
    return services.campaigns.create(data.model_dump())


@router.put("/streams/{stream_id}", response_model=StreamResponse)
def publish(stream_id: int, data: StreamDraft, services: Services = Depends(get_services)):
    return services.streams.publish(stream_id, data.model_dump())


@router.post("/streams/{stream_id}/accept", response_model=StreamResponse)
def accept_remote(stream_id: int, services: Services = Depends(get_services)):
    return services.streams.accept_remote(stream_id)
