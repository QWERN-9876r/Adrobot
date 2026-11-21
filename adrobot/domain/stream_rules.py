"""Pure stream payload, offer and revision rules."""
import hashlib
import json
from adrobot.domain.errors import Problem

GOOGLE = "https://www.google.com/"

def stream_payloads(campaign_id, country, offer_id):
    return [
        {"campaign_id": campaign_id, "name": f"{country} → Google", "type": "regular",
         "position": 1, "state": "active", "collect_clicks": True,
         "filter_or": False, "offers": [], "landings": [], "triggers": [], "schema": "redirect", "action_type": "http",
         "action_payload": GOOGLE, "filters": [{"name": "country", "mode": "accept", "payload": [country]}]},
        {"campaign_id": campaign_id, "name": "Ротация офферов", "type": "default",
         "position": 2, "state": "active", "collect_clicks": True,
         "filter_or": False, "filters": [], "landings": [], "triggers": [], "schema": "landings", "action_type": "http",
         "offers": [{"offer_id": offer_id, "share": 100, "state": "active"}]},
    ]


def country_filter(item, country):
    payload = item.get("payload")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            payload = [payload]
    return item.get("name") == "country" and item.get("mode") == "accept" and payload == [country]


def positive(value):
    if type(value) is not int or value <= 0:
        raise Problem("Выберите доступный вариант.")
    return value


def offer_entries(stream):
    return [{"offer_id": positive(item["offer_id"]), "share": item["share"],
             "state": item.get("state", "active")} for item in stream.get("offers") or []]


def revision(stream, entries, version=0):
    digest = [version, stream.get("updated_at"), stream.get("schema"), stream.get("state"), stream.get("campaign_id"),
              sorted(entries, key=lambda item: item["offer_id"])]
    return hashlib.sha256(json.dumps(digest, sort_keys=True).encode()).hexdigest()


def ordered(offers):
    return sorted(offers, key=lambda item: item["offer_id"])
