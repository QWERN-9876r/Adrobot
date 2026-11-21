import type { CatalogItem } from '../../api/types';

export function SelectOptions({ items, placeholder, showIds = false }: {
  items: CatalogItem[];
  placeholder: string;
  showIds?: boolean;
}) {
  return (
    <>
      <option value="">{placeholder}</option>
      {items.map(({ id, name }) => (
        <option key={id} value={id}>{showIds ? `${name} · #${id}` : name}</option>
      ))}
    </>
  );
}
