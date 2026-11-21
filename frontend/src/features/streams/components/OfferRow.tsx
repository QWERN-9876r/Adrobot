import type { DraftAction } from '../model/shares';

export function OfferRow({ id, share, state, name, pinned, onEdit }: {
  id: number;
  share: number;
  state: 'active' | 'disabled' | 'removed';
  name: string | undefined;
  pinned: boolean;
  onEdit: (action: DraftAction) => boolean;
}) {
  const pinLabel = pinned ? 'Открепить' : 'Закрепить';
  return (
    <tr className={state !== 'active' ? 'inactive' : undefined}>
      <td><strong>{name ?? 'Оффер'}</strong><small>#{id}</small></td>
      <td>
        {state === 'active' ? (
          <div className="share">
            <span>{share}%</span>
            <meter min={0} max={100} value={share} aria-label={`Доля оффера #${id}`} />
          </div>
        ) : <span className="share inactive-share">0% · {state === 'removed' ? 'удалён' : 'отключён'}</span>}
      </td>
      <td>
        <div className="row-actions">
          {state === 'active' ? (
            <button type="button" className={pinned ? 'pin selected' : 'pin'}
              aria-label={`${pinLabel} долю оффера #${id}`}
              onClick={() => onEdit({ type: 'toggle-pin', offerId: id })}>
              <span aria-hidden="true">Закрепить</span>
              <span aria-hidden="true">Открепить</span>
            </button>
          ) : (
            <button type="button" className="text-button" disabled={state === 'removed' && !name}
              aria-label={`Восстановить оффер #${id}`}
              onClick={() => onEdit({ type: 'add', offerId: id })}>
              Восстановить
            </button>
          )}
          {state !== 'removed' && (
            <button type="button" className="remove" aria-label={`Удалить оффер #${id}`}
              onClick={() => onEdit({ type: 'remove', offerId: id })}>
              Удалить
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}
