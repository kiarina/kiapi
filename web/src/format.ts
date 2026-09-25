export function gb(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${Number(value.toFixed(1))} GB`;
}

export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  const units = ["KB", "MB", "GB"];
  let v = n / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v >= 100 ? 0 : 1)} ${units[i]}`;
}

export function duration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || seconds < 0) return "—";
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  if (m < 60) return `${m}m ${s.toString().padStart(2, "0")}s`;
  return `${Math.floor(m / 60)}h ${(m % 60).toString().padStart(2, "0")}m`;
}

export function ago(ts: number, now: number): string {
  const d = Math.max(0, now - ts);
  if (d < 45) return "just now";
  if (d < 3600) return `${Math.round(d / 60)}m ago`;
  if (d < 86400) return `${Math.round(d / 3600)}h ago`;
  return new Date(ts * 1000).toLocaleDateString();
}

export function shortId(id: string): string {
  const [prefix, rest] = id.includes("_") ? id.split(/_(.+)/) : ["", id];
  if (!rest || rest.length <= 10) return id;
  return `${prefix}_${rest.slice(0, 4)}…${rest.slice(-4)}`;
}

// First paragraph of a Markdown description, for one-line summaries.
export function firstParagraph(md: string | undefined): string {
  if (!md) return "";
  return md.trim().split(/\n\s*\n/)[0].replace(/\s+/g, " ").replace(/[`*]/g, "");
}
