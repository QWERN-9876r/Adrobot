import { object } from './validation';
import type { Decoder } from './validation';

export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly code: string) {
    super(message);
  }
}

export async function request<T>(path: string, decode: Decoder<T>, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch('/api' + path, init);
  } catch {
    throw new ApiError('Нет связи с сервером. Результат записи может быть неизвестен. Проверьте состояние перед повтором.', 0, 'uncertain');
  }

  const result: unknown = await response.json().catch(() => null);
  if (!response.ok || result === null) {
    throw new ApiError(object(result) && typeof result.error === 'string'
      ? result.error
      : `Не удалось получить ответ от API (HTTP ${response.status}).`, response.status,
      object(result) && typeof result.code === 'string' ? result.code : 'error');
  }
  if (!decode(result)) throw new ApiError('API вернул данные неожиданного формата. Проверьте результат операции.', 502, 'upstream_contract');
  return result;
}

export function json(method: 'POST' | 'PUT', body: object): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}
