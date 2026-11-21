"""Idempotent campaign creation and recovery of interrupted attempts."""
import hashlib
from sqlalchemy.orm import Session
from adrobot.domain.countries import COUNTRY_CODES
from adrobot.domain.errors import Problem
from adrobot.domain.tracker import OPTIONS, Tracker
from adrobot.domain.stream_rules import positive, stream_payloads
from adrobot.domain.creation_rules import verify_campaign, verify_streams
from adrobot.infrastructure.models import CreationOperation
from adrobot.infrastructure.locking import resource_lock
from .catalog import CatalogService


class CampaignCreationService:
    def __init__(self, session: Session, api: Tracker):
        self.session = session
        self.api = api
        self.tracker = api.identity
        self.catalog = CatalogService(api)

    def create(self, data):
        key = data["operation_id"]
        payload = {k: v for k, v in data.items() if k != "operation_id"}
        with resource_lock(self.session, self.tracker, f"create:{key}"):
            operation = self.session.get(CreationOperation, (self.tracker, key))
            if operation and operation.payload != payload:
                raise Problem("Сначала завершите предыдущую попытку создания с прежними параметрами.", 409, "conflict")
            if operation and operation.data.get("result"):
                return operation.data["result"]
            if payload['country'].strip().upper() not in COUNTRY_CODES:
                raise Problem('Выберите действующий двухбуквенный код страны.')
            if operation is None:
                name = payload["name"].strip()
                if not name or len(name) > 120:
                    raise Problem("Введите название кампании длиной до 120 символов.")
                catalog = self.catalog.load()
                for category in OPTIONS:
                    if positive(payload[category]) not in {row['id'] for row in catalog[category]}:
                        raise Problem("Один из выбранных вариантов недоступен. Обновите список.")
                operation = CreationOperation(tracker=self.tracker, key=key, payload=payload,
                                              data={"phase": "new", "attempted": []})
                self.session.add(operation)
                self.session.commit()
            return self._create(operation)

    def _checkpoint(self, operation, **changes):
        operation.data = {**operation.data, **changes}
        self.session.commit()

    def _create(self, operation):
        data = operation.payload
        alias = 'adrobot-' + hashlib.sha256(operation.key.encode()).hexdigest()[:32]
        campaign_id = operation.data.get('campaign_id')
        if campaign_id is None:
            matches = [row for row in self.api.call('/campaigns') if row.get('alias') == alias]
            if len(matches) > 1:
                raise Problem('Найдено несколько кампаний этой операции. Проверьте Keitaro.', 409, 'conflict')
            if matches:
                campaign_id = matches[0]['id']
            elif operation.data['phase'] != 'new':
                raise Problem(f'Результат создания неизвестен. Проверьте кампанию с alias {alias} в Keitaro и повторите проверку. Новый POST не отправлен.', 409, 'uncertain')
            else:
                self._checkpoint(operation, phase='creating')
                try:
                    campaign = self.api.call('/campaigns', 'POST', {
                        'name': data['name'].strip(), 'alias': alias, 'state': 'disabled',
                        'type': 'position', 'domain_id': data['domains'], 'group_id': str(data['groups']),
                        'traffic_source_id': data['sources'],
                    })
                except Problem as error:
                    raise Problem('Ответ создания не подтверждён. Повторите проверку этой же операции.', 502, 'uncertain') from error
                campaign_id = campaign['id']
            self._checkpoint(operation, campaign_id=campaign_id, phase='configuring')
        path = f'/campaigns/{campaign_id}'
        campaign = self.api.call(path)
        if campaign['state'] == 'deleted':
            raise Problem(f'Кампания #{campaign_id} удалена. Восстановите её в Keitaro для продолжения.', 409, 'conflict')
        verify_campaign(campaign, data)
        expected = stream_payloads(campaign_id, data['country'].strip().upper(), data['offers'])
        for desired in expected:
            saved = self.api.call(path + '/streams')
            matches = [row for row in saved if row.get('type') == desired['type'] and row.get('state') != 'deleted']
            if matches:
                continue
            if desired['type'] in operation.data['attempted']:
                raise Problem(f'Создание потока кампании #{campaign_id} не подтверждено. Проверьте Keitaro; повторный POST не отправлен.', 409, 'uncertain')
            self._checkpoint(operation, attempted=[*operation.data['attempted'], desired['type']])
            try:
                self.api.call('/streams', 'POST', desired)
            except Problem as error:
                raise Problem(f'Результат создания потока кампании #{campaign_id} неизвестен. Повторите проверку.', 502, 'uncertain') from error
        campaign = self._verify_created(path, data)
        if campaign['state'] != 'active':
            self._checkpoint(operation, phase='enabling')
            try:
                self.api.call(path + '/enable', 'POST')
            except Problem as error:
                try:
                    enabled = self.api.call(path)['state'] == 'active'
                except Problem:
                    enabled = False
                if not enabled:
                    raise Problem(f'Включение кампании #{campaign_id} не подтверждено. Повторите проверку.',
                                  502, 'uncertain') from error
        result = self._verify_created(path, data)
        if result['state'] != 'active':
            raise Problem('Кампания ещё не активна. Повторите проверку.', 409, 'uncertain')
        self._checkpoint(operation, phase='complete', result=result)
        return result

    def _verify_created(self, path, data):
        campaign = self.api.call(path)
        streams = self.api.call(path + '/streams')
        try:
            verify_campaign(campaign, data)
            verify_streams(campaign['id'], streams, data['country'].strip().upper(), data['offers'])
        except Problem as error:
            if campaign.get('state') == 'active':
                # This operation owns the new campaign. Do not leave traffic
                # enabled after discovering an invalid creation result.
                try:
                    try:
                        self.api.call(path + '/disable', 'POST')
                    except Problem:
                        pass  # The state read below also covers a lost response.
                    if self.api.call(path).get('state') != 'disabled':
                        raise Problem('Отключение не подтверждено.')
                except Problem as disable_error:
                    raise Problem(f'Кампания #{campaign["id"]} не соответствует ТЗ; отключение не подтверждено. Проверьте Keitaro.',
                                  502, 'uncertain') from disable_error
            raise error
        return campaign
