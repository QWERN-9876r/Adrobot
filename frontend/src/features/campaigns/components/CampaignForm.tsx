import { useRef, useState } from 'react';
import type { FormEvent, SubmitEvent } from 'react';
import type { CampaignInput, Catalog, CatalogCategory } from '../../../api/types';
import { readAttempt, saveAttempt, clearAttempt } from '../model/creationStorage';
import type { CreationAttempt } from '../model/creationStorage';
import { SelectOptions } from '../../../shared/ui/SelectOptions';
import { OfferSearch } from '../../../shared/ui/OfferSearch';

const catalogFields = [
  { key: 'domains', label: 'Домен', placeholder: 'Выберите домен' },
  { key: 'groups', label: 'Группа', placeholder: 'Выберите группу' },
  { key: 'sources', label: 'Источник трафика', placeholder: 'Выберите источник' },
] as const;
const countryNames = new Intl.DisplayNames('ru', { type: 'region' });
const requiredMessages: Record<string, string> = {
  name: 'Введите название кампании.',
  country: 'Выберите страну.',
  offers: 'Введите название или ID оффера Keitaro.',
  domains: 'Выберите домен.',
  groups: 'Выберите группу.',
  sources: 'Выберите источник трафика.',
};

function localizeValidation(event: FormEvent<HTMLFormElement>) {
  const field = event.target;
  if (!(field instanceof HTMLInputElement || field instanceof HTMLSelectElement)) return;
  if (field.name === 'offers' && field.validity.patternMismatch) {
    field.setCustomValidity('Выберите оффер из подсказок или введите его ID.');
  } else if (field.validity.valueMissing) {
    field.setCustomValidity(requiredMessages[field.name] ?? 'Заполните это поле.');
  }
}

function clearValidation(event: FormEvent<HTMLFormElement>) {
  const field = event.target;
  if (field instanceof HTMLInputElement || field instanceof HTMLSelectElement) field.setCustomValidity('');
}

export function CampaignForm({ catalog, busy, onCreate, onStartNew }: {
  catalog: Catalog | null;
  busy: boolean;
  onCreate: (input: CampaignInput & { operation_id: string }) => Promise<boolean | 'discarded'>;
  onStartNew: () => void;
}) {
  const formRef = useRef<HTMLFormElement>(null);
  const [stored, setStored] = useState(() => {
    try { return { attempt: readAttempt(), error: '' }; }
    catch (error) { return { attempt: null, error: error instanceof Error ? error.message : 'Хранилище недоступно.' }; }
  });
  async function runAttempt(attempt: CreationAttempt) {
    const created = await onCreate({ ...attempt.input, operation_id: attempt.operation_id });
    if (created === true || created === 'discarded') {
      try {
        clearAttempt();
        setStored({ attempt: null, error: '' });
      } catch {
        setStored({ attempt, error: 'Кампания создана, но очистить сохранённую попытку не удалось.' });
      }
    }
    return created === true;
  }
  const [selections, setSelections] = useState<Record<CatalogCategory, string>>({
    offers: '', domains: '', groups: '', sources: '',
  });
  const countries = (catalog?.countries ?? []).map(code => ({ code, name: countryNames.of(code) ?? code }))
    .sort((first, second) => first.name.localeCompare(second.name, 'ru'));
  const selectedOffer = catalog?.offers.find(offer => offer.id === Number(selections.offers));

  function startNewCampaign() {
    try {
      clearAttempt();
    } catch {
      setStored(previous => ({ ...previous, error: 'Не удалось закрыть попытку в хранилище вкладки.' }));
      return;
    }
    formRef.current?.reset();
    setSelections({ offers: '', domains: '', groups: '', sources: '' });
    setStored({ attempt: null, error: '' });
    onStartNew();
  }

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = new FormData(form);
    const offerId = Number(fields.get('offers'));
    if (!Number.isSafeInteger(offerId) || offerId <= 0) {
      const field = form.elements.namedItem('offers');
      if (field instanceof HTMLInputElement) {
        field.setCustomValidity('Введите корректный ID оффера Keitaro.');
        field.reportValidity();
      }
      return;
    }
    let attempt: CreationAttempt;
    try {
      attempt = saveAttempt({
        name: String(fields.get('name')),
        country: String(fields.get('country')),
        offers: offerId,
        domains: Number(fields.get('domains')),
        groups: Number(fields.get('groups')),
        sources: Number(fields.get('sources')),
      });
      setStored({ attempt, error: '' });
    } catch {
      setStored({ attempt: null, error: 'Не удалось сохранить попытку. Разрешите хранилище вкладки и повторите.' });
      return;
    }
    const created = await runAttempt(attempt);
    if (created) {
      form.reset();
      setSelections({ offers: '', domains: '', groups: '', sources: '' });
    }
  }

  return (
    <section className="panel create-panel" aria-labelledby="create-title">
      <div className="panel-header"><h2 id="create-title">Новая кампания</h2></div>
      {stored.error && <p role="alert" className="empty">{stored.error}</p>}
      {stored.attempt && <div className="empty">
        <p>Сохранена попытка создания «{stored.attempt.input.name}». Проверка продолжит её без повторного создания кампании.</p>
        <p>Можно закрыть попытку в этой вкладке и создать другую кампанию. Состояние предыдущей кампании можно проверить в Keitaro.</p>
        <div className="creation-actions">
          <button type="button" disabled={busy} onClick={() => { if (stored.attempt) void runAttempt(stored.attempt); }}>Проверить и продолжить</button>
          <button type="button" className="secondary" disabled={busy} onClick={startNewCampaign}>Начать новую кампанию</button>
        </div>
      </div>}
      <form ref={formRef} onSubmit={submit} onInvalid={localizeValidation} onInput={clearValidation}>
        <fieldset disabled={busy || !catalog || !!stored.attempt || !!stored.error} className="create-fields">
          <label>Название кампании<input name="name" required maxLength={120} placeholder="Запуск в Австралии" /></label>
          <label>
            Страна
            <select name="country" required defaultValue="">
              <option value="">Выберите страну</option>
              {countries.map(({ code, name }) => <option key={code} value={code}>{name} · {code}</option>)}
            </select>
          </label>
          <div>
            <OfferSearch label="Оффер Keitaro" name="offers" offers={catalog?.offers ?? []} value={selections.offers}
              onChange={value => setSelections(previous => ({ ...previous, offers: value }))}
              onSelect={offer => setSelections(previous => ({ ...previous, offers: String(offer.id) }))} />
            {selectedOffer && <small>{selectedOffer.name}</small>}
          </div>
          {catalogFields.map(({ key, label, placeholder }) => {
            const items = catalog?.[key] ?? [];
            const selected = items.some(item => String(item.id) === selections[key]) ? selections[key] : '';
            return (
              <label key={key}>
                {label}
                <select name={key} value={selected} required onChange={event => {
                  const value = event.target.value;
                  setSelections(previous => ({ ...previous, [key]: value }));
                }}>
                  <SelectOptions items={items} placeholder={placeholder} />
                </select>
              </label>
            );
          })}
          <div className="route-preview">
            <div><span>Выбранная страна</span><span aria-hidden="true">→</span><strong>Google</strong></div>
            <div><span>Остальной трафик</span><span aria-hidden="true">→</span><strong>Оффер</strong></div>
          </div>
          <button type="submit">Создать кампанию</button>
        </fieldset>
      </form>
    </section>
  );
}
