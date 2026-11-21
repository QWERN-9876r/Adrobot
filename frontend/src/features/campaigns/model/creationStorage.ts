import type { CampaignInput } from '../../../api/types';

export interface CreationAttempt {
  operation_id: string;
  input: CampaignInput;
}
const key = 'adrobot.creation.v1';

export function readAttempt(): CreationAttempt | null {
  const raw = sessionStorage.getItem(key);
  if (!raw) return null;
  const value = JSON.parse(raw) as Partial<CreationAttempt>;
  if (typeof value.operation_id !== 'string' || !value.input
    || typeof value.input.name !== 'string' || typeof value.input.country !== 'string'
    || ![value.input.offers, value.input.domains, value.input.groups, value.input.sources].every(Number.isSafeInteger)) {
    throw new Error('Не удалось прочитать предыдущую попытку. Проверьте созданные кампании перед очисткой данных вкладки.');
  }
  return value as CreationAttempt;
}

export function saveAttempt(input: CampaignInput): CreationAttempt {
  const attempt = { operation_id: crypto.randomUUID(), input };
  sessionStorage.setItem(key, JSON.stringify(attempt));
  return attempt;
}

export function clearAttempt() {
  sessionStorage.removeItem(key);
}
