"""Local tracker adapter backed by SQLAlchemy."""
import re
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from adrobot.domain.errors import Problem
from .models import DemoRecord

class Demo:
    mode = "demo"
    identity = "demo"

    def __init__(self, session: Session):
        self.session = session

    def call(self, path, method="GET", body=None):
        if method == "POST":
            if path.endswith(("/enable", "/disable")):
                entity, action = path.rsplit("/", 1)
                return self.call(entity, "PUT", {"state": "active" if action == "enable" else "disabled"})
            record = DemoRecord(path=path, data={})
            self.session.add(record)
            self.session.flush()
            record.data = {"id": record.id, "state": "active", **body}
            return record.data

        campaign_streams = re.fullmatch(r"/campaigns/(\d+)/streams", path)
        if campaign_streams:
            campaign_id = int(campaign_streams[1])
            return [row for row in self.call("/streams") if row["campaign_id"] == campaign_id]

        item = re.fullmatch(r"(/\w+)/(\d+)", path)
        if item:
            record = self.session.scalar(select(DemoRecord).where(
                DemoRecord.path == item[1],
                func.json_extract(DemoRecord.data, "$.id") == int(item[2]),
            ))
            if record is None:
                raise Problem("Запись не найдена.", 404)
            if method != "GET":
                updates = body if method == "PUT" else {"state": "deleted"}
                record.data = {**record.data, **updates}
            return record.data

        records = self.session.scalars(select(DemoRecord).where(DemoRecord.path == path).order_by(DemoRecord.id))
        return [record.data for record in records if record.data["state"] != "deleted"]
