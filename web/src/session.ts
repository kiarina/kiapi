import { useSyncExternalStore } from "react";

import { getToken } from "./api";

function subscribe(cb: () => void) {
  window.addEventListener("kiapi:token", cb);
  return () => window.removeEventListener("kiapi:token", cb);
}

export function useToken(): string {
  return useSyncExternalStore(subscribe, getToken);
}

export type Theme = "light" | "dark";
const THEME_KEY = "kiapi.theme";

export function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    // Fall through to the system preference.
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(theme: Theme, persist: boolean): void {
  document.documentElement.dataset.theme = theme;
  if (!persist) return;
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // The choice then lasts for this page only.
  }
}
