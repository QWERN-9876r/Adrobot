import type { CampaignInput, Stream, Draft } from './types';
import { request, json } from './client';
import { arrayOf } from './validation';
import { isCatalog, isItem, isStream } from './decoders';

export const api = {
  catalog: (signal?: AbortSignal) => request('/catalog', isCatalog, { signal }),
  campaigns: (signal?: AbortSignal) => request('/campaigns', arrayOf(isItem), { signal }),
  streams: (campaignId: number, signal?: AbortSignal) =>
    request(`/campaigns/${campaignId}/streams`, arrayOf(isStream), { signal }),
  create: (input: CampaignInput & { operation_id: string }) => request('/campaigns', isItem, json('POST', input)),
  accept: (id: number) => request(`/streams/${id}/accept`, isStream, json('POST', {})),
  publish: (stream: Stream, draft: Draft) =>
    request(`/streams/${stream.id}`, isStream, json('PUT', {
      offers: draft.offers,
      pins: draft.pins,
      revision: stream.revision,
    })),
};
