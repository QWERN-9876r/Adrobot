export interface CatalogItem {
  id: number;
  name: string;
}

export interface Catalog extends Record<CatalogCategory, CatalogItem[]> {
  mode: 'demo' | 'live';
  countries: string[];
}

export type CatalogCategory = 'offers' | 'domains' | 'groups' | 'sources';

export interface CampaignInput extends Record<CatalogCategory, number> {
  name: string;
  country: string;
}

export interface Offer {
  offer_id: number;
  share: number;
  state: 'active' | 'disabled';
}

export interface Draft {
  offers: Offer[];
  pins: number[];
  removed: number[];
}

export interface Stream extends Draft {
  id: number;
  name: string;
  schema: string;
  state: string;
  revision: string;
  operation_state: 'ready' | 'uncertain';
}
