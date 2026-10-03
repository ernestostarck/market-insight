import { useSyncExternalStore } from 'react';
import { STORAGE_KEYS } from '@/lib/constants';
import { queryClient } from '@/lib/query-client';

/**
 * Market segment picked on the Rubros page: a whole rubro (`cat:<code>`) or a
 * single concept (`concept:<code>`). While set, lib/api.ts sends it as the
 * `segmento` query param on every GET, so the backend scopes analytics and
 * lists to that segment (see app/nlp/segmento.py).
 */
export interface Segmento {
  code: string;
  label: string;
  /** Parent rubro name, for concepts. */
  parentLabel?: string;
}

const listeners = new Set<() => void>();

function readStored(): Segmento | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.segmento);
    return raw ? (JSON.parse(raw) as Segmento) : null;
  } catch {
    return null;
  }
}

let current: Segmento | null = typeof window !== 'undefined' ? readStored() : null;

export function getSegmento(): Segmento | null {
  return current;
}

export function setSegmento(next: Segmento | null): void {
  if ((current?.code ?? null) === (next?.code ?? null)) return;
  current = next;
  try {
    if (next) localStorage.setItem(STORAGE_KEYS.segmento, JSON.stringify(next));
    else localStorage.removeItem(STORAGE_KEYS.segmento);
  } catch {
    // Storage unavailable (private mode): the selection still applies for this session.
  }
  listeners.forEach((listener) => listener());
  // Every cached query was fetched for the previous segment.
  void queryClient.resetQueries();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useSegmento(): Segmento | null {
  return useSyncExternalStore(subscribe, getSegmento, getSegmento);
}
