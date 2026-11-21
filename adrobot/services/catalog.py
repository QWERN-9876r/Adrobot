"""Read-only campaign and catalog queries."""
from adrobot.domain.tracker import OPTIONS, Tracker


class CatalogService:
    def __init__(self, api: Tracker):
        self.api = api
        self.mode = api.mode

    def campaigns(self):
        return [{"id": row["id"], "name": row["name"], "state": row["state"]}
                for row in self.api.call("/campaigns") if row["state"] != "deleted"]

    def load(self):
        return {name: [{"id": row["id"], "name": row["name"]} for row in self.api.call(path)
                       if row.get("state", "active") == "active"] for name, path in OPTIONS.items()}
