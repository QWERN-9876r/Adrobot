import { test } from 'node:test';
import assert from 'node:assert/strict';
import { load } from './helpers/load-typescript.mjs';

const { api } = await load('api/campaigns');
const { ApiError } = await load('api/client');

test('API rejects malformed success and preserves conflict classification', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response(JSON.stringify([{ id: 'bad', name: 'bad' }]));
    await assert.rejects(api.campaigns(), error => error instanceof ApiError && error.code === 'upstream_contract');
    globalThis.fetch = async () => new Response(JSON.stringify({ error: 'Changed', code: 'conflict' }), { status: 409 });
    await assert.rejects(api.campaigns(), error => error.status === 409 && error.code === 'conflict');
  } finally { globalThis.fetch = original; }
});
