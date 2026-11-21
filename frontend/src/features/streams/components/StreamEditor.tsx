import { useState } from 'react';
import type { CatalogItem, Draft, Stream } from '../../../api/types';
import type { DraftAction } from '../model/shares';
import { OfferPicker } from './OfferPicker';
import { OfferRow } from './OfferRow';

export function StreamEditor({ stream, draft, catalogOffers, onEdit, onPublish, onCancel, onAccept }: {
  stream: Stream;
  draft: Draft | undefined;
  catalogOffers: CatalogItem[];
  onEdit: (action: DraftAction) => boolean;
  onPublish: () => void;
  onCancel: () => void;
  onAccept: () => void;
}) {
  const [addingFirst, setAddingFirst] = useState(false);
  const current = draft ?? stream;
  const editable = stream.schema === 'landings';
  const labels = new Map(catalogOffers.map(offer => [offer.id, offer.name]));
  const rows = [...current.offers, ...current.removed.map(offer_id => ({
    offer_id, share: 0, state: 'removed' as const,
  }))];
  const linked = new Set(rows.map(offer => offer.offer_id));
  const active = current.offers.filter(offer => offer.state === 'active');
  const allocated = active.reduce((sum, offer) => sum + offer.share, 0);
  const canChooseOffer = current.offers.length > 0 || addingFirst;
  const pickerOffers = catalogOffers.filter(offer => !linked.has(offer.id));

  return (
    <section className={draft ? 'stream draft' : 'stream'} aria-labelledby={`stream-${stream.id}`}>
      <div className="stream-header">
        <div className="stream-title">
          <span aria-hidden="true" className={`stream-marker${editable ? ' rotation' : ''}`}>{editable ? '⇄' : '↗'}</span>
          <h3 id={`stream-${stream.id}`}>{stream.name}</h3>
        </div>
        {editable && (rows.length > 0 || draft) && (
          <span className="draft-label" aria-hidden={!draft}>Неопубликованные изменения</span>
        )}
        {editable && !canChooseOffer && stream.operation_state === 'ready' && pickerOffers.length > 0 && (
          <button type="button" className="secondary" onClick={() => setAddingFirst(true)}>Добавить первый оффер</button>
        )}
      </div>
      {stream.operation_state === 'uncertain' && <div className="empty" role="alert">
        <p>Предыдущая публикация не подтверждена. Ниже показано текущее состояние Keitaro. Проверьте его перед продолжением.</p>
        <button type="button" className="secondary" onClick={onAccept}>Принять состояние Keitaro</button>
      </div>}
      {editable && (rows.length > 0 || canChooseOffer || draft) && (
        <fieldset disabled={stream.operation_state === 'uncertain'}>
          {rows.length > 0 && (
            <table>
              <thead><tr><th scope="col">Оффер</th><th scope="col">Доля</th><th scope="col">Действия</th></tr></thead>
              <tbody>
                {rows.map(({ offer_id: id, share, state }) => (
                  <OfferRow key={id} id={id} share={share} state={state} name={labels.get(id)}
                    pinned={current.pins.includes(id)} onEdit={onEdit} />
                ))}
              </tbody>
              {active.length > 0 && <tfoot><tr><th scope="row">Всего</th><td>{allocated}%</td><td /></tr></tfoot>}
            </table>
          )}
          {canChooseOffer && <OfferPicker available={pickerOffers} onAdd={id => {
            const added = onEdit({ type: 'add', offerId: id });
            if (added) setAddingFirst(false);
            return added;
          }} />}
          {draft && (
            <div className="publish">
              <button type="button" className="secondary" onClick={onCancel}>Отменить изменения</button>
              <button type="button" onClick={onPublish}>Опубликовать в Keitaro</button>
            </div>
          )}
        </fieldset>
      )}
    </section>
  );
}
