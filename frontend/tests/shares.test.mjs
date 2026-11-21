import { test } from 'node:test';
import assert from 'node:assert/strict';
import { load } from './helpers/load-typescript.mjs';

const { editDraft } = await load('features/streams/model/shares');
const offer = (offer_id, share) => ({ offer_id, share, state: 'active' });

test('adding and removing keep integer shares summing to 100', () => {
  let draft = { offers: [], pins: [], removed: [] };
  for (let id = 1; id <= 100; id++) {
    const previous = structuredClone(draft);
    const next = editDraft(draft, { type: 'add', offerId: id });
    assert.deepEqual(draft, previous);
    draft = next;
    assert.equal(draft.offers.reduce((sum, item) => sum + item.share, 0), 100);
    assert.ok(draft.offers.every(item => Number.isInteger(item.share) && item.share >= 0));
  }
  assert.throws(() => editDraft(draft, { type: 'add', offerId: 101 }));
  for (let id = 100; id > 1; id--) {
    draft = editDraft(draft, { type: 'remove', offerId: id });
    assert.equal(draft.offers.reduce((sum, item) => sum + item.share, 0), 100);
  }
});

test('adding or restoring an offer preserves the draft when a pin consumes the whole share', () => {
  const draft = { offers: [offer(1, 100)], pins: [1], removed: [2] };
  const original = structuredClone(draft);
  for (const offerId of [2, 3]) {
    assert.throws(() => editDraft(draft, { type: 'add', offerId }), /открепите/i);
    assert.deepEqual(draft, original);
  }
});

test('pinned share stays fixed through add/remove/restore', () => {
  let draft = { offers: [offer(1, 25), offer(2, 75)], pins: [1], removed: [] };
  for (const action of [{ type: 'add', offerId: 3 }, { type: 'remove', offerId: 2 }, { type: 'add', offerId: 2 }]) {
    draft = editDraft(draft, action);
    assert.equal(draft.offers.find(item => item.offer_id === 1).share, 25);
    assert.equal(draft.offers.reduce((sum, item) => sum + item.share, 0), 100);
  }
  assert.deepEqual(draft.removed, []);
});

test('impossible pinned allocation leaves the original draft intact', () => {
  const draft = { offers: [offer(1, 25), offer(2, 75)], pins: [1], removed: [] };
  assert.throws(() => editDraft(draft, { type: 'remove', offerId: 2 }));
  assert.equal(draft.offers.length, 2);
});


test('editor distributes three offers as 33/33/34 and restores an archived offer', () => {
  const original = { offers: [offer(1, 100)], pins: [], removed: [] };
  let draft = editDraft(original, { type: 'add', offerId: 2 });
  draft = editDraft(draft, { type: 'add', offerId: 3 });
  assert.deepEqual(draft.offers.map(item => item.share), [33, 33, 34]);
  assert.deepEqual(original.offers, [offer(1, 100)]);
  draft = editDraft(draft, { type: 'remove', offerId: 2 });
  assert.deepEqual(draft.offers.map(item => item.share), [50, 50]);
  assert.deepEqual(draft.removed, [2]);
  draft = editDraft(draft, { type: 'add', offerId: 2 });
  assert.deepEqual(draft.removed, []);
  assert.equal(draft.offers.length, 3);
  assert.equal(draft.offers.reduce((sum, item) => sum + item.share, 0), 100);
});

test('pinning 25 percent leaves 37 and 38 percent for two other offers', () => {
  const draft = { offers: [offer(1, 25), offer(2, 75)], pins: [1], removed: [] };
  const added = editDraft(draft, { type: 'add', offerId: 3 });
  assert.deepEqual(added.offers.map(item => item.share), [25, 37, 38]);
});
