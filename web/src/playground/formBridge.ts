import { useSyncExternalStore } from "react";

import type { Field, Operation, Values } from "./schema";

// Lets the floating assistant fill the form on the current page. A playground
// registers itself; the assistant turns each operation into a `fill_*` tool.
export interface FormBridge {
  family: string;
  operations: Operation[];
  current: string;
  models: string[];
  apply: (operation: string, values: Values) => void;
}

let bridge: FormBridge | null = null;
const listeners = new Set<() => void>();

export function setFormBridge(next: FormBridge | null): void {
  bridge = next;
  listeners.forEach((l) => l());
}

export function useFormBridge(): FormBridge | null {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => bridge,
  );
}

export function toolName(op: Operation): string {
  return `fill_${op.name.replace(/[^A-Za-z0-9_]/g, "_")}_form`;
}

type JsonSchema = Record<string, unknown>;

function short(text: string): string {
  const one = text.replace(/\s+/g, " ").trim();
  return one.length > 280 ? `${one.slice(0, 277)}…` : one;
}

function fieldSchema(f: Field, models: string[]): JsonSchema | null {
  const description = short(f.description);
  switch (f.kind) {
    case "model":
      return models.length ? { type: "string", enum: models, description } : { type: "string", description };
    case "prompt":
    case "text":
      return { type: "string", description };
    case "integer":
    case "number":
      return {
        type: f.kind,
        description,
        ...(f.minimum !== undefined ? { minimum: f.minimum } : {}),
        ...(f.maximum !== undefined ? { maximum: f.maximum } : {}),
      };
    case "enum":
      return { type: "string", enum: f.options, description };
    case "boolean":
      return { type: "boolean", description };
    case "file":
      return { type: "string", description: `Files API file_id (file_...). ${description}` };
    case "files":
      return { type: "array", items: { type: "string" }, description: `Files API file_ids. ${description}` };
    case "tags":
      return { type: "array", items: f.options ? { type: "string", enum: f.options } : { type: "string" }, description };
    case "json":
      return { description: `JSON value. ${description}` };
    default:
      return null;
  }
}

export function fillTools(b: FormBridge): unknown[] {
  return b.operations.map((op) => {
    const properties: Record<string, JsonSchema> = {};
    for (const f of op.fields) {
      const s = fieldSchema(f, b.models);
      if (s) properties[f.name] = s;
    }
    return {
      type: "function",
      function: {
        name: toolName(op),
        description: `Fill the "${op.name}" form on the user's screen. Include only the fields you want to set. The user reviews the form and submits it; nothing runs yet.`,
        parameters: { type: "object", properties },
      },
    };
  });
}

export interface FillResult {
  values: Values;
  applied: string[];
  skipped: string[];
}

// Keeps only arguments that fit the form; anything else is skipped, never guessed.
export function valuesFromArgs(op: Operation, args: Record<string, unknown>, models: string[]): FillResult {
  const out: FillResult = { values: {}, applied: [], skipped: [] };
  for (const [name, v] of Object.entries(args)) {
    const f = op.fields.find((x) => x.name === name);
    const value = f ? coerce(f, v, models) : undefined;
    if (value === undefined) {
      out.skipped.push(name);
    } else {
      out.values[name] = value;
      out.applied.push(name);
    }
  }
  return out;
}

function coerce(f: Field, v: unknown, models: string[]): unknown {
  if (v === null || v === undefined) return undefined;
  switch (f.kind) {
    case "model":
      return typeof v === "string" && (models.length === 0 || models.includes(v)) ? v : undefined;
    case "prompt":
    case "text":
      if (typeof v === "string") return v;
      if (typeof v === "number") return String(v);
      return typeof v === "object" ? JSON.stringify(v, null, 2) : undefined;
    case "integer":
    case "number": {
      const n = typeof v === "number" ? v : typeof v === "string" && v.trim() !== "" ? Number(v) : Number.NaN;
      if (!Number.isFinite(n) || (f.kind === "integer" && !Number.isInteger(n))) return undefined;
      if ((f.minimum !== undefined && n < f.minimum) || (f.maximum !== undefined && n > f.maximum)) return undefined;
      return String(n);
    }
    case "enum":
      return typeof v === "string" && f.options?.includes(v) ? v : undefined;
    case "boolean":
      return typeof v === "boolean" ? v : v === "true" ? true : v === "false" ? false : undefined;
    case "file":
      return typeof v === "string" && v.startsWith("file_") ? v : undefined;
    case "files":
      return Array.isArray(v) && v.every((x) => typeof x === "string" && x.startsWith("file_")) ? v : undefined;
    case "tags":
      return Array.isArray(v) && v.every((x) => typeof x === "string" && (!f.options || f.options.includes(x))) ? v : undefined;
    case "json":
      return typeof v === "string" ? v : JSON.stringify(v, null, 2);
    default:
      return undefined;
  }
}
