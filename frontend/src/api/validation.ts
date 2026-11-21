export type Decoder<T> = (value: unknown) => value is T;
export const object = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;
export const integer = (value: unknown): value is number => Number.isSafeInteger(value);
export const arrayOf = <T>(decode: Decoder<T>): Decoder<T[]> => (value): value is T[] => Array.isArray(value) && value.every(decode);
