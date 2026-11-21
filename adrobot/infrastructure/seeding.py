"""Initial sample data for demo mode."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from adrobot.domain.tracker import OPTIONS
from adrobot.domain.stream_rules import stream_payloads
from .models import DemoRecord
from .demo import Demo

def seed_demo(session: Session):
    if session.scalar(select(DemoRecord.id).limit(1)) is not None:
        return

    api = Demo(session)
    labels = {
        "offers": ["Стартовый оффер", "Мобильный оффер", "Летний оффер", "Партнёрский оффер", "Новый креатив"],
        "domains": ["demo.example"],
        "groups": ["Привлечение"],
        "sources": ["Платная реклама в соцсетях"],
    }
    for category, path in OPTIONS.items():
        for item_id, label in enumerate(labels[category], 1):
            api.call(path, "POST", {"name": label, "id": item_id})
    campaign = api.call("/campaigns", "POST", {"name": "Запуск в Австралии", "alias": "australia-rollout"})
    redirect, fallback = stream_payloads(campaign["id"], "AU", 1)
    fallback["offers"] = [
        {"offer_id": offer_id, "share": share, "state": "active"}
        for offer_id, share in enumerate([33, 33, 34], 1)
    ]
    api.call("/streams", "POST", redirect)
    api.call("/streams", "POST", fallback)
