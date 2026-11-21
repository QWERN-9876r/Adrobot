"""Offer publication with conflict detection and durable recovery."""
from sqlalchemy.orm import Session
from adrobot.domain.errors import Problem
from adrobot.domain.tracker import Tracker
from adrobot.domain.stream_rules import offer_entries, ordered, positive, revision
from adrobot.infrastructure.locking import resource_lock
from .history import StreamHistoryService


class StreamService:
    def __init__(self, session: Session, api: Tracker):
        self.session = session
        self.api = api
        self.tracker = api.identity
        self.history = StreamHistoryService(session, api.identity)

    def list(self, campaign_id):
        rows = self.api.call(f"/campaigns/{campaign_id}/streams")
        result = []
        for row in rows:
            with resource_lock(self.session, self.tracker, f"stream:{row['id']}"):
                stream = self.api.call(f"/streams/{row['id']}")
                if stream.get("state") != "deleted":
                    result.append(self.history.reconcile(stream))
        return result

    def accept_remote(self, stream_id):
        with resource_lock(self.session, self.tracker, f'stream:{stream_id}'):
            return self.history.reconcile(self.api.call(f'/streams/{stream_id}'), accept=True)

    def publish(self, stream_id, data):
        with resource_lock(self.session, self.tracker, f'stream:{stream_id}'):
            return self._publish(stream_id, data)

    def _publish(self, stream_id, data):
        path = f'/streams/{stream_id}'
        stream = self.api.call(path)
        view = self.history.reconcile(stream)
        if view['operation_state'] == 'uncertain':
            raise Problem('Предыдущая публикация не подтверждена. Загрузите потоки и проверьте состояние Keitaro.', 409, 'uncertain')
        if stream.get('schema') != 'landings' or stream.get('state') == 'deleted':
            raise Problem('В этом потоке нельзя редактировать офферы.')
        if data.get('revision') != view['revision']:
            raise Problem('Поток или закрепления изменились. Загрузите потоки заново перед публикацией.', 409, 'conflict')
        existing = offer_entries(stream)
        previously_active = {item['offer_id'] for item in existing if item['state'] == 'active'}
        clean, ids = [], set()
        valid_ids = {item['offer_id'] for item in existing}
        valid_ids.update(row['id'] for row in self.api.call('/offers') if row.get('state') == 'active')
        for offer in data['offers']:
            offer_id = positive(offer['offer_id'])
            share, state = offer['share'], offer['state']
            if offer_id in ids or offer_id not in valid_ids or type(share) is not int or not 0 <= share <= 100 or state not in {'active', 'disabled'}:
                raise Problem('В черновике указан недоступный оффер или неверная доля.')
            if state == 'active' and share == 0 and offer_id not in previously_active:
                raise Problem('Новому или восстановленному офферу нужна доля больше 0%.')
            ids.add(offer_id)
            clean.append({'offer_id': offer_id, 'share': share, 'state': state})
        pins = sorted(set(map(positive, data['pins'])))
        active = {item['offer_id'] for item in clean if item['state'] == 'active'}
        if not set(pins) <= active or (active and sum(item['share'] for item in clean if item['state'] == 'active') != 100):
            raise Problem('Сумма активных долей должна составлять 100%. Закреплять можно только активные офферы.')
        # Check again after potentially slow catalog validation. This narrows the
        # upstream race; without remote compare-and-set it cannot eliminate it.
        latest = self.api.call(path)
        if revision(latest, offer_entries(latest)) != revision(stream, existing):
            raise Problem('Поток изменился во время подготовки публикации. Загрузите его заново.', 409, 'conflict')
        if ordered(existing) == ordered(clean):
            return self.history.reconcile(latest, pins)
        record = self.history.get(stream_id)
        record.data = {**record.data, 'pending': {'offers': clean, 'pins': pins}}
        self.session.commit()  # Durable intent BEFORE the remote mutation.
        try:
            self.api.call(path, 'PUT', {'offers': clean})
        except Problem:
            # A lost write response is not proof of a failed write; reconcile.
            pass
        try:
            saved = self.api.call(path)
        except Problem as error:
            raise Problem('Результат публикации неизвестен. Загрузите потоки для проверки; повторная запись не отправляется.', 502, 'uncertain') from error
        result = self.history.reconcile(saved)
        if result['operation_state'] == 'uncertain':
            raise Problem('Keitaro вернул другое состояние. Загрузите потоки и проверьте результат перед следующей публикацией.', 409, 'uncertain')
        return result
