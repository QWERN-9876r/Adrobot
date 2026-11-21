"""Acceptance rules for the two-stream campaign described in the specification."""
from .errors import Problem
from .stream_rules import GOOGLE, country_filter, offer_entries


def verify_campaign(campaign, data):
    checks = {
        'название': campaign.get('name') == data['name'].strip(),
        'домен': campaign.get('domain_id') == data['domains'],
        'группа': str(campaign.get('group_id')) == str(data['groups']),
        'источник': campaign.get('traffic_source_id') == data['sources'],
        'ротация по позиции': campaign.get('type') == 'position',
        'состояние': campaign.get('state') in {'active', 'disabled'},
    }
    failed = [name for name, valid in checks.items() if not valid]
    if failed:
        raise Problem('Настройки созданной кампании не соответствуют ТЗ: ' + ', '.join(failed) + '.',
                      409, 'configuration_mismatch')


def verify_streams(campaign_id, streams, country, offer_id):
    live = [stream for stream in streams if stream.get('state') != 'deleted']
    if len(live) != 2:
        raise Problem('В созданной кампании должно быть ровно два потока.', 409, 'configuration_mismatch')
    first = next((stream for stream in live if stream.get('position') == 1), {})
    second = next((stream for stream in live if stream.get('position') == 2), {})
    filters = first.get('filters') or []
    checks = {
        'порядок потоков': bool(first) and bool(second),
        'принадлежность кампании': all(stream.get('campaign_id') == campaign_id for stream in live),
        'активность обоих потоков': all(stream.get('state') == 'active' for stream in live),
        'первый поток': first.get('type') == 'regular' and first.get('schema') == 'redirect',
        'HTTP-перенаправление на Google': first.get('action_type') == 'http' and first.get('action_payload') == GOOGLE,
        'единственный фильтр выбранной страны': len(filters) == 1 and country_filter(filters[0], country),
        'отсутствие офферов в первом потоке': not first.get('offers'),
        'второй поток по умолчанию': second.get('type') == 'default' and second.get('schema') == 'landings',
        'отсутствие фильтров второго потока': not second.get('filters'),
        'единственный выбранный оффер, 100%': offer_entries(second) == [
            {'offer_id': offer_id, 'share': 100, 'state': 'active'}],
        'прямой переход без лендингов': all(not stream.get('landings') for stream in live),
        'отсутствие дополнительных триггеров': all(not stream.get('triggers') for stream in live),
    }
    failed = [name for name, valid in checks.items() if not valid]
    if failed:
        raise Problem('Потоки созданной кампании не соответствуют ТЗ: ' + ', '.join(failed) + '.',
                      409, 'configuration_mismatch')
