import type { Draft, Offer } from '../../../api/types';

function rebalance(offers: Offer[], pins: number[]): Offer[] {
  const active = offers.filter(offer => offer.state === 'active');
  const fixed = active.filter(offer => pins.includes(offer.offer_id));
  const adjustable = active.filter(offer => !pins.includes(offer.offer_id));
  const remaining = 100 - fixed.reduce((sum, offer) => sum + offer.share, 0);

  if (remaining < 0 || (active.length > 0 && adjustable.length === 0 && remaining !== 0)) {
    throw new Error('Открепите долю одного из активных офферов, чтобы сумма долей составила 100%.');
  }
  if (adjustable.length === 0) return offers;

  const base = Math.floor(remaining / adjustable.length);
  const extra = remaining % adjustable.length;
  const shares = new Map(adjustable.map((offer, index) => [
    offer.offer_id,
    base + Number(index >= adjustable.length - extra),
  ]));
  return offers.map(offer => {
    const share = shares.get(offer.offer_id);
    return share === undefined ? offer : { ...offer, share };
  });
}

export interface DraftAction {
  type: 'add' | 'remove' | 'toggle-pin';
  offerId: number;
}

export function editDraft(draft: Draft, { type, offerId }: DraftAction): Draft {
  const { offers, pins, removed } = draft;
  switch (type) {
    case 'add': {
      const offer = offers.find(item => item.offer_id === offerId);
      const nextOffers: Offer[] = offer
        ? offers.map(item => item === offer ? { ...item, state: 'active' } : item)
        : [...offers, { offer_id: offerId, state: 'active', share: 0 }];
      const balanced = rebalance(nextOffers, pins);
      if (balanced.some(item => item.state === 'active' && !pins.includes(item.offer_id) && item.share === 0)) {
        throw new Error('Для каждого незакреплённого оффера нужен минимум 1%. Открепите долю или удалите лишний оффер.');
      }
      return { offers: balanced, pins, removed: removed.filter(id => id !== offerId) };
    }
    case 'remove': {
      const nextPins = pins.filter(id => id !== offerId);
      return {
        offers: rebalance(offers.filter(item => item.offer_id !== offerId), nextPins),
        pins: nextPins,
        removed: [...removed, offerId],
      };
    }
    case 'toggle-pin':
      return { offers, pins: pins.includes(offerId) ? pins.filter(id => id !== offerId) : [...pins, offerId], removed };
  }
}
