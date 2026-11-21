import { useId, useState } from 'react';
import type { SubmitEvent } from 'react';
import type { CatalogItem } from '../../../api/types';
import { OfferSearch } from '../../../shared/ui/OfferSearch';

export function OfferPicker({ available, onAdd }: {
  available: CatalogItem[];
  onAdd: (id: number) => boolean;
}) {
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<number | null>(null);
  const selectedMatch = available.find(offer => offer.id === selected);
  const emptyId = useId();
  const noOffers = available.length === 0;

  function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedMatch && onAdd(selectedMatch.id)) {
      setSearch('');
      setSelected(null);
    }
  }

  return (
    <form className="offer-picker" onSubmit={submit}>
      <OfferSearch label="Поиск оффера" offers={available} value={search} descriptionId={noOffers ? emptyId : undefined}
        onChange={value => { setSearch(value); setSelected(null); }}
        onSelect={offer => { setSearch(offer.name); setSelected(offer.id); }} />
      <button type="submit" className="secondary" disabled={!selectedMatch}>Добавить оффер</button>
      {noOffers && <p className="offer-search-empty" id={emptyId}>Нет офферов для добавления</p>}
    </form>
  );
}
