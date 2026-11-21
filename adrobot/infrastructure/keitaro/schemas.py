"""Validation at the Keitaro HTTP boundary."""
import re
from typing import Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, StrictInt, ValidationError, Field, field_validator
from adrobot.domain.errors import Problem
from adrobot.domain.tracker import OPTIONS

class Entity(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: StrictInt = Field(gt=0)
    name: str
    state: str = "active"


class RemoteOffer(BaseModel):
    model_config = ConfigDict(extra="allow")
    offer_id: StrictInt = Field(gt=0)
    share: StrictInt = Field(ge=0, le=100)
    state: Literal["active", "disabled"] = "active"


class RemoteCampaign(Entity):
    state: str


class RemoteFilter(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    mode: str
    payload: object


class RemoteStream(Entity):
    campaign_id: StrictInt
    schema_name: str = Field(alias="schema")
    offers: list[RemoteOffer] = Field(default_factory=list)
    filters: list[RemoteFilter] = Field(default_factory=list)

    @field_validator('offers', 'filters', mode='before')
    @classmethod
    def empty_offers(cls, value):
        return [] if value is None else value


def validate_response(path, method, value):
    path = urlsplit(path).path
    # Validate the boundary before business code accesses fields.
    model = RemoteStream if path.startswith('/streams') or path.endswith('/streams') else Entity
    if path.startswith('/campaigns') and not path.endswith('/streams'):
        model = RemoteCampaign
    collection = method == 'GET' and (path in {urlsplit(value).path for value in OPTIONS.values()} or path == '/campaigns' or path.endswith('/streams'))
    try:
        toggle = re.fullmatch(r'/campaigns/([1-9][0-9]*)/(?:enable|disable)', path) if method == 'POST' else None
        if toggle:
            # The deployed tracker can wrap the campaign in a one-element array.
            if isinstance(value, list):
                if len(value) != 1:
                    raise ValueError('Expected exactly one campaign')
                value = value[0]
            campaign = RemoteCampaign.model_validate(value)
            if campaign.id != int(toggle[1]):
                raise ValueError('Expected the requested campaign')
            return campaign.model_dump(by_alias=True)
        if collection:
            if not isinstance(value, list):
                raise ValueError('Expected array')
            return [model.model_validate(row).model_dump(by_alias=True) for row in value]
        return model.model_validate(value).model_dump(by_alias=True)
    except (ValidationError, ValueError, TypeError) as error:
        raise Problem('Keitaro вернул данные неожиданного формата.', 502, 'upstream_contract') from error
