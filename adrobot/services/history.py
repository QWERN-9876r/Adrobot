"""Reconciliation of remote streams with durable local history."""
from sqlalchemy.orm import Session
from adrobot.domain.stream_rules import offer_entries, ordered, revision
from adrobot.infrastructure.models import StreamHistory


class StreamHistoryService:
    def __init__(self, session: Session, tracker: str):
        self.session = session
        self.tracker = tracker

    def get(self, stream_id):
        record = self.session.get(StreamHistory, (self.tracker, stream_id))
        if record is None:
            record = StreamHistory(tracker=self.tracker, stream=stream_id,
                                   data={'known': [], 'pins': [], 'version': 0})
            self.session.add(record)
        return record

    def reconcile(self, stream, pins=None, accept=False):
        entries = offer_entries(stream)
        record = self.get(stream['id'])
        history = record.data
        pending = history.get('pending')
        if pending and ordered(entries) == ordered(pending['offers']) and stream.get('schema') == 'landings' and stream.get('state') != 'deleted':
            pins = pending['pins']
            pending = None
        if accept:
            pending = None
        current = {item['offer_id'] for item in entries}
        active = {item['offer_id'] for item in entries if item['state'] == 'active'}
        known = sorted(current.union(history['known']))
        pinned = sorted(active.intersection(history['pins'] if pins is None else pins))
        data = {'known': known, 'pins': pinned, 'pending': pending}
        changed = any(history.get(key) != value for key, value in data.items())
        version = history.get('version', 0) + int(changed)
        record.data = {**data, 'version': version}
        self.session.commit()
        return {'id': stream['id'], 'name': stream['name'], 'schema': stream['schema'],
                'state': stream['state'], 'offers': entries, 'pins': pinned,
                'removed': sorted(set(known) - current), 'revision': revision(stream, entries, version),
                'operation_state': 'uncertain' if pending else 'ready'}
