import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

import { AuthError, apiFetch, apiJson } from "./api";

export interface Remote<T> {
  data: T | undefined;
  error: Error | undefined;
  loading: boolean;
  reload: () => void;
}

// Fetches `path` and refetches every `intervalMs` while the tab is visible.
export function useApi<T>(path: string | null, intervalMs?: number): Remote<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(path !== null);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    if (path === null) return;
    let alive = true;
    setLoading(true);
    apiJson<T>(path)
      .then((d) => {
        if (!alive) return;
        setData(d);
        setError(undefined);
      })
      .catch((e: Error) => {
        if (!alive) return;
        setError(e);
        if (e instanceof AuthError) window.dispatchEvent(new Event("kiapi:unauthorized"));
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [path, tick]);

  useEffect(() => {
    if (!intervalMs || path === null) return;
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") reload();
    }, intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs, path, reload]);

  return { data, error, loading, reload };
}

// Resolves a file download URL. Images and media cannot send an Authorization
// header, so with a token the bytes are fetched and exposed as an object URL.
export function useFileSrc(path: string | null, token: string): string | undefined {
  const [src, setSrc] = useState<string>();
  useEffect(() => {
    if (!path) return;
    if (!token) {
      setSrc(path);
      return;
    }
    let url: string | undefined;
    let alive = true;
    apiFetch(path)
      .then((r) => r.blob())
      .then((b) => {
        if (!alive) return;
        url = URL.createObjectURL(b);
        setSrc(url);
      })
      .catch(() => alive && setSrc(undefined));
    return () => {
      alive = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [path, token]);
  return src;
}

function subscribeHash(cb: () => void) {
  window.addEventListener("hashchange", cb);
  return () => window.removeEventListener("hashchange", cb);
}

// Hash routes (`#/models`) keep every UI path clear of the API's URL space.
export function useRoute(): string[] {
  const hash = useSyncExternalStore(subscribeHash, () => window.location.hash);
  return hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
}

export function useNow(intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now() / 1000), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs]);
  return now;
}

export function useCopy(): [string | null, (text: string) => void] {
  const [copied, setCopied] = useState<string | null>(null);
  const timer = useRef<number>(undefined);
  const copy = useCallback((text: string) => {
    void navigator.clipboard?.writeText(text);
    setCopied(text);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopied(null), 1400);
  }, []);
  return [copied, copy];
}
