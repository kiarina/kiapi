import { useEffect, useMemo, useState } from "react";

import { apiJson, type OpenApiDoc, type SetupModel } from "./api";

export const DOMAIN_ORDER = ["chat", "embedding", "image", "audio", "video", "web"];

export interface Family {
  domain: string;
  family: string;
  models: SetupModel[];
}

export interface DomainGroup {
  domain: string;
  families: Family[];
}

export function specBase(domain: string, family: string): string {
  return domain === family ? `/v1/${domain}` : `/v1/${domain}/${family}`;
}

export function familyHref(domain: string, family: string, tab?: string): string {
  return `#/f/${domain}/${family}${tab ? `/${tab}` : ""}`;
}

export function groupFamilies(models: SetupModel[]): DomainGroup[] {
  const byKey = new Map<string, Family>();
  for (const m of models) {
    const key = `${m.domain}/${m.family}`;
    if (!byKey.has(key)) byKey.set(key, { domain: m.domain, family: m.family, models: [] });
    byKey.get(key)!.models.push(m);
  }
  const rank = (d: string) => {
    const i = DOMAIN_ORDER.indexOf(d);
    return i === -1 ? DOMAIN_ORDER.length : i;
  };
  const domains = [...new Set([...byKey.values()].map((f) => f.domain))].sort(
    (a, b) => rank(a) - rank(b) || a.localeCompare(b),
  );
  return domains.map((domain) => ({
    domain,
    families: [...byKey.values()].filter((f) => f.domain === domain),
  }));
}

const specCache = new Map<string, Promise<OpenApiDoc>>();

export function loadSpec(domain: string, family: string): Promise<OpenApiDoc> {
  const url = `${specBase(domain, family)}/openapi.json`;
  if (!specCache.has(url)) {
    const p = apiJson<OpenApiDoc>(url);
    p.catch(() => specCache.delete(url));
    specCache.set(url, p);
  }
  return specCache.get(url)!;
}

// "kiapi Qwen Image API" -> "Qwen Image"
export function displayTitle(doc: OpenApiDoc | undefined, fallback: string): string {
  const t = doc?.info.title?.replace(/^kiapi\s+/, "").replace(/\s+API$/, "");
  return t || fallback;
}

export function useSpecs(families: Family[]): Record<string, OpenApiDoc> {
  const [specs, setSpecs] = useState<Record<string, OpenApiDoc>>({});
  const key = useMemo(() => families.map((f) => `${f.domain}/${f.family}`).join(","), [families]);
  useEffect(() => {
    let alive = true;
    for (const f of families) {
      loadSpec(f.domain, f.family)
        .then((doc) => alive && setSpecs((s) => ({ ...s, [f.family]: doc })))
        .catch(() => undefined);
    }
    return () => {
      alive = false;
    };
  }, [key]);
  return specs;
}
