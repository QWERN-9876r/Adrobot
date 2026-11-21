import type { CatalogItem, Offer, Stream, Catalog } from './types';
import { object, integer, arrayOf } from './validation';
import type { Decoder } from './validation';

export const isItem: Decoder<CatalogItem> = (value): value is CatalogItem => object(value) && integer(value.id) && typeof value.name === 'string';
export const isOffer: Decoder<Offer> = (value): value is Offer => object(value) && integer(value.offer_id) && integer(value.share)
  && value.share >= 0 && value.share <= 100 && (value.state === 'active' || value.state === 'disabled');
export const isStream: Decoder<Stream> = (value): value is Stream => object(value) && isItem(value) && typeof value.schema === 'string'
  && typeof value.state === 'string' && typeof value.revision === 'string'
  && arrayOf(isOffer)(value.offers) && arrayOf(integer)(value.pins) && arrayOf(integer)(value.removed)
  && (value.operation_state === 'ready' || value.operation_state === 'uncertain');
export const isCatalog: Decoder<Catalog> = (value): value is Catalog => object(value) && (value.mode === 'demo' || value.mode === 'live')
  && Array.isArray(value.countries) && value.countries.every(code => typeof code === 'string' && /^[A-Z]{2}$/.test(code))
  && ['offers', 'domains', 'groups', 'sources'].every(key => arrayOf(isItem)(value[key]));
