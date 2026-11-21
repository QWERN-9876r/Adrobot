"""Validated HTTP inputs and outputs; remote representations live in tracker.py."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt


class CampaignInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    operation_id: str = Field(pattern=r'^[a-zA-Z0-9-]{16,64}$')
    name: str = Field(min_length=1, max_length=120)
    country: str = Field(pattern=r'^[A-Za-z]{2}$')
    offers: StrictInt = Field(gt=0)
    domains: StrictInt = Field(gt=0)
    groups: StrictInt = Field(gt=0)
    sources: StrictInt = Field(gt=0)


class OfferInput(BaseModel):
    offer_id: StrictInt = Field(gt=0)
    share: StrictInt = Field(ge=0, le=100)
    state: Literal['active', 'disabled']


class StreamDraft(BaseModel):
    revision: str = Field(pattern=r'^[a-f0-9]{64}$')
    offers: list[OfferInput]
    pins: list[StrictInt]


class CatalogItem(BaseModel):
    id: StrictInt
    name: str


class CampaignResponse(CatalogItem):
    state: str


class CatalogResponse(BaseModel):
    mode: Literal['demo', 'live']
    countries: list[str]
    offers: list[CatalogItem]
    domains: list[CatalogItem]
    groups: list[CatalogItem]
    sources: list[CatalogItem]


class StreamResponse(CampaignResponse):
    schema_name: str = Field(alias='schema')
    offers: list[OfferInput]
    pins: list[StrictInt]
    removed: list[StrictInt]
    revision: str
    operation_state: Literal['ready', 'uncertain']
