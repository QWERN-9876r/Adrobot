import { test } from 'node:test';
import assert from 'node:assert/strict';
import { load } from './helpers/load-typescript.mjs';

const { readAttempt, saveAttempt, clearAttempt } = await load('features/campaigns/model/creationStorage');

test('creation attempt retains the same identity after reload', () => {
  const original = globalThis.sessionStorage;
  const store = new Map();
  globalThis.sessionStorage = { getItem: key => store.get(key) ?? null, setItem: (key, value) => store.set(key, value), removeItem: key => store.delete(key) };
  try {
    const input = { name: 'Test', country: 'AU', offers: 1, domains: 1, groups: 1, sources: 1 };
    const saved = saveAttempt(input);
    assert.deepEqual(readAttempt(), saved);
    clearAttempt();
    assert.equal(readAttempt(), null);
  } finally { globalThis.sessionStorage = original; }
});
