import type { OpenApiDoc, OpenApiOperation, SchemaRef } from "../api";

export type FieldKind =
  | "model"
  | "prompt"
  | "text"
  | "integer"
  | "number"
  | "enum"
  | "boolean"
  | "file"
  | "files"
  | "loras"
  | "tags"
  | "json";

export interface Field {
  name: string;
  kind: FieldKind;
  label: string;
  description: string;
  required: boolean;
  defaultValue: unknown;
  options?: string[];
  minimum?: number;
  maximum?: number;
  // A text field whose schema also accepts an integer (seedvr2's resolution).
  acceptsInteger?: boolean;
  advanced: boolean;
}

export interface Operation {
  method: "get" | "post";
  path: string;
  name: string;
  description: string;
  fields: Field[];
  // Generation endpoints take `mode`; the UI always submits async and follows the job.
  async: boolean;
}

// Fields shown before "Advanced". Everything else is folded away.
const BASIC = new Set([
  "model",
  "prompt",
  "negative_prompt",
  "lyrics",
  "query",
  "text",
  "url",
  "image",
  "images",
  "init_image",
  "end_image",
  "audio",
  "source",
  "dataset",
  "width",
  "height",
  "duration",
  "num_frames",
  "seed",
  "preset",
  "resolution",
  "targets",
  "training_mode",
  "start",
  "end",
  "strength",
  "image_strength",
]);

const PROMPT_FIELDS = new Set(["prompt", "negative_prompt", "lyrics", "text"]);

export function resolveRef(doc: OpenApiDoc, schema: SchemaRef | undefined): SchemaRef | undefined {
  if (!schema?.$ref) return schema;
  return doc.components?.schemas?.[schema.$ref.split("/").pop()!];
}

function refName(s: SchemaRef | undefined): string | undefined {
  return s?.$ref?.split("/").pop();
}

function nonNull(s: SchemaRef): SchemaRef[] {
  const union = s.anyOf ?? s.oneOf;
  return union ? union.filter((u) => u.type !== "null") : [s];
}

function classify(doc: OpenApiDoc, name: string, prop: SchemaRef): Pick<Field, "kind" | "options"> {
  if (name === "model") return { kind: "model" };
  const variants = nonNull(prop);
  const v = variants[0] ?? {};
  const resolved = resolveRef(doc, v);
  if (variants.length > 1) {
    // e.g. ideogram4's prompt (string or caption object) or seedvr2's resolution (int or "4k").
    return { kind: variants.some((x) => x.type === "string") && PROMPT_FIELDS.has(name) ? "prompt" : "text" };
  }
  if (refName(v) === "FileRef") return { kind: "file" };
  if (v.type === "array" && refName(v.items) === "FileRef") return { kind: "files" };
  if (v.type === "array" && refName(v.items) === "LoraRef") return { kind: "loras" };
  if (v.type === "array" && (v.items?.type === "string" || v.items?.enum)) {
    return { kind: "tags", options: v.items?.enum?.map(String) };
  }
  if (resolved?.enum) return { kind: "enum", options: resolved.enum.map(String) };
  if (v.enum) return { kind: "enum", options: v.enum.map(String) };
  if (v.type === "boolean") return { kind: "boolean" };
  if (v.type === "integer") return { kind: "integer" };
  if (v.type === "number") return { kind: "number" };
  if (v.type === "string") return { kind: PROMPT_FIELDS.has(name) ? "prompt" : "text" };
  return { kind: "json" };
}

const ACRONYMS: Record<string, string> = { url: "URL", fps: "FPS", lora: "LoRA", cfg: "CFG" };

function label(name: string): string {
  const s = name
    .split("_")
    .map((w) => ACRONYMS[w] ?? w)
    .join(" ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function fieldFrom(doc: OpenApiDoc, name: string, prop: SchemaRef, required: boolean): Field {
  const v = nonNull(prop)[0] ?? {};
  return {
    name,
    ...classify(doc, name, prop),
    label: label(name),
    description: prop.description ?? v.description ?? "",
    required,
    defaultValue: prop.default,
    minimum: v.minimum,
    maximum: v.maximum,
    acceptsInteger: nonNull(prop).some((x) => x.type === "integer"),
    advanced: !BASIC.has(name) && !required,
  };
}

export function operationsOf(doc: OpenApiDoc): Operation[] {
  const ops: Operation[] = [];
  for (const [path, methods] of Object.entries(doc.paths)) {
    if (path.endsWith("/models")) continue;
    for (const [method, op] of Object.entries(methods) as [string, OpenApiOperation & { parameters?: Param[] }][]) {
      if (method === "post") {
        const content = op.requestBody?.content ?? {};
        const schema = resolveRef(doc, Object.values(content)[0]?.schema);
        const required = new Set(schema?.required ?? []);
        const props = Object.entries(schema?.properties ?? {});
        ops.push({
          method,
          path,
          name: path.split("/").pop() ?? path,
          description: op.description ?? "",
          async: props.some(([n]) => n === "mode"),
          fields: props
            .filter(([n]) => n !== "mode" && n !== "stream" && n !== "stream_options")
            .map(([n, p]) => fieldFrom(doc, n, p, required.has(n))),
        });
      } else if (method === "get" && op.parameters?.some((p) => p.in === "query")) {
        ops.push({
          method,
          path,
          name: path.split("/").pop() ?? path,
          description: op.description ?? "",
          async: false,
          fields: op.parameters
            .filter((p) => p.in === "query")
            .map((p) => fieldFrom(doc, p.name, { ...p.schema, description: p.description ?? p.schema?.description }, !!p.required)),
        });
      }
    }
  }
  return ops;
}

interface Param {
  name: string;
  in: string;
  required?: boolean;
  description?: string;
  schema?: SchemaRef;
}

export type Values = Record<string, unknown>;

function isEmpty(v: unknown): boolean {
  return v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);
}

// Only values the user set are sent, so the server keeps filling model-dependent defaults.
export function buildPayload(op: Operation, values: Values): Values {
  const out: Values = {};
  for (const f of op.fields) {
    const v = values[f.name];
    if (isEmpty(v)) continue;
    switch (f.kind) {
      case "integer":
        out[f.name] = Number.parseInt(String(v), 10);
        break;
      case "number":
        out[f.name] = Number.parseFloat(String(v));
        break;
      case "file":
        out[f.name] = { type: "file_id", file_id: v };
        break;
      case "files":
        out[f.name] = (v as string[]).map((id) => ({ type: "file_id", file_id: id }));
        break;
      case "loras":
        out[f.name] = (v as { file: string; scale: number }[]).map((l) => ({
          file: { type: "file_id", file_id: l.file },
          scale: l.scale,
        }));
        break;
      case "json":
        out[f.name] = typeof v === "string" ? JSON.parse(v) : v;
        break;
      case "text":
        // Unions such as seedvr2's resolution accept a number or a named preset.
        out[f.name] = f.acceptsInteger && /^-?\d+$/.test(String(v)) ? Number(v) : v;
        break;
      case "prompt":
        // ideogram4 also takes a JSON caption object in `prompt`.
        out[f.name] = typeof v === "string" && /^\s*\{/.test(v) ? safeJson(v) : v;
        break;
      default:
        out[f.name] = v;
    }
  }
  if (op.async) out.mode = "async";
  return out;
}

function safeJson(s: string): unknown {
  try {
    return JSON.parse(s);
  } catch {
    return s;
  }
}

// Turns a job's recorded params back into form values (for "Reuse settings").
export function valuesFromParams(op: Operation, params: Record<string, unknown>): Values {
  const out: Values = {};
  for (const f of op.fields) {
    const v = params[f.name] ?? params[`${f.name}_file_id`];
    if (v === undefined || v === null) continue;
    if (f.kind === "file") {
      const id = typeof v === "string" ? v : (v as { file_id?: string }).file_id;
      if (id) out[f.name] = id;
    } else if (f.kind === "files" && Array.isArray(v)) {
      out[f.name] = v.map((x) => (typeof x === "string" ? x : (x as { file_id?: string }).file_id)).filter(Boolean);
    } else if (f.kind === "loras") {
      continue;
    } else if (f.kind === "json" || (typeof v === "object" && f.kind !== "tags")) {
      out[f.name] = JSON.stringify(v, null, 2);
    } else {
      out[f.name] = f.kind === "integer" || f.kind === "number" ? String(v) : v;
    }
  }
  return out;
}
