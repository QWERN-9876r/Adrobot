import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { CatalogItem } from '../../api/types';

export function OfferSearch({ label, offers, value, onChange, onSelect, name, descriptionId }: {
  label: string;
  offers: CatalogItem[];
  value: string;
  onChange: (value: string) => void;
  onSelect: (offer: CatalogItem) => void;
  name?: string;
  descriptionId?: string;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const listId = `${id}-options`;
  const query = value.trim().replace(/^#/, '').toLowerCase();
  const [settledQuery, setSettledQuery] = useState('');
  const [focused, setFocused] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [activeId, setActiveId] = useState<number | null>(null);
  const showSuggestions = offers.length > 0 || !descriptionId;

  useEffect(() => {
    if (!query || !focused || dismissed || !showSuggestions) return;
    const timer = window.setTimeout(() => setSettledQuery(query), 250);
    return () => window.clearTimeout(timer);
  }, [value, query, focused, dismissed, showSuggestions]);

  const showResults = focused && !dismissed && showSuggestions && query !== '' && settledQuery === query;
  const matches = showResults ? offers.filter(offer =>
    String(offer.id).includes(query) || offer.name.toLowerCase().includes(query),
  ) : [];
  const expanded = matches.length > 0;
  const activeIndex = matches.findIndex(offer => offer.id === activeId);
  const activeOffer = matches[activeIndex];
  const activeOption = activeOffer ? `${listId}-${activeOffer.id}` : undefined;

  useEffect(() => {
    if (activeOption) document.getElementById(activeOption)?.scrollIntoView({ block: 'nearest' });
  }, [activeOption]);

  function close() {
    setDismissed(true);
    setActiveId(null);
  }

  function choose(offer: CatalogItem) {
    close();
    input.current?.setCustomValidity('');
    onSelect(offer);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.nativeEvent.isComposing) return;
    if (event.key === 'Escape' && query && !dismissed) {
      event.preventDefault();
      close();
    } else if (event.key === 'Enter' && activeOffer) {
      event.preventDefault();
      choose(activeOffer);
    } else if (expanded && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
      event.preventDefault();
      const nextIndex = event.key === 'ArrowDown' ? Math.min(activeIndex + 1, matches.length - 1)
        : activeIndex < 0 ? matches.length - 1 : Math.max(activeIndex - 1, 0);
      setActiveId(matches[nextIndex]?.id ?? null);
    }
  }

  return (
    <div className="offer-search">
      <label htmlFor={id}>{label}</label>
      <input ref={input} id={id} type="text" role="combobox" aria-autocomplete="list" aria-expanded={expanded}
        aria-controls={expanded ? listId : undefined} aria-activedescendant={activeOption}
        aria-describedby={descriptionId} autoComplete="off"
        name={name} required={!!name} pattern={name ? '0*[1-9][0-9]*' : undefined}
        placeholder="Название или ID" value={value}
        onFocus={() => { setFocused(true); setDismissed(false); }}
        onBlur={() => { setFocused(false); setActiveId(null); }}
        onChange={event => {
          setSettledQuery('');
          setDismissed(false);
          setActiveId(null);
          onChange(event.target.value);
        }}
        onKeyDown={handleKeyDown} />
      {showResults && (expanded ? (
        <ul className="offer-search-popup" role="listbox" id={listId} aria-label="Результаты поиска офферов">
          {matches.map(offer => (
            <li id={`${listId}-${offer.id}`} key={offer.id} role="option" aria-selected={offer.id === activeId}
              onMouseDown={event => event.preventDefault()} onClick={() => choose(offer)}>
              <span>{offer.name}</span><small>#{offer.id}</small>
            </li>
          ))}
        </ul>
      ) : <p className="offer-search-popup" role="status">По запросу ничего не найдено</p>)}
    </div>
  );
}
