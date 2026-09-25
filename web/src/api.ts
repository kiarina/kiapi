const TOKEN_KEY = "kiapi.token";

export class AuthError extends Error {}

export function getToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setToken(token: string): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Storage can be unavailable (private mode).
  }
  window.dispatchEvent(new Event("kiapi:token"));
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401) throw new AuthError("unauthorized");
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // Keep the status line.
    }
    throw new Error(detail);
  }
  return res;
}

export async function apiJson<T>(path: string): Promise<T> {
  return (await apiFetch(path)).json() as Promise<T>;
}

export const downloadPath = (fileId: string) => `/v1/files/${fileId}/download`;

// --- API shapes (the subset the UI reads) -------------------------------------

export interface ResidentModel {
  name: string;
  family: string;
  domain: string;
  weight_gb: number;
  idle_s: number;
}

export interface Health {
  status: string;
  warm: boolean;
  queue_len: number;
  memory: { loaded: ResidentModel[]; resident_gb: number; budget_gb: number };
}

export interface SetupResource {
  kind: string;
  label: string;
  ready: boolean;
  disk_gb: number | null;
  detail: string;
  activate_command: string;
}

export interface SetupModel {
  domain: string;
  family: string;
  name: string;
  default: boolean;
  status: "ready" | "missing" | "none";
  size_gb: number;
  resources: SetupResource[];
}

export interface Setup {
  summary: {
    models_total: number;
    models_ready: number;
    resources_total: number;
    resources_ready: number;
    installed_gb: number;
    total_gb: number;
  };
  data: SetupModel[];
}

export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "canceled";

export interface Job {
  id: string;
  type: string;
  status: JobStatus;
  params: Record<string, unknown>;
  result: unknown;
  artifacts: string[];
  error: string | null;
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
  progress: number | null;
  progress_label: string;
}

export interface FileRecord {
  file_id: string;
  filename: string;
  content_type: string;
  size: number;
  created_at: number;
  meta: Record<string, unknown>;
}

export interface ListEnvelope<T> {
  data: T[];
}

export interface OpenApiOperation {
  summary?: string;
  description?: string;
  requestBody?: { content?: Record<string, { schema?: SchemaRef }> };
}

export interface SchemaRef {
  $ref?: string;
  type?: string;
  title?: string;
  description?: string;
  default?: unknown;
  enum?: unknown[];
  anyOf?: SchemaRef[];
  oneOf?: SchemaRef[];
  items?: SchemaRef;
  properties?: Record<string, SchemaRef>;
  required?: string[];
  minimum?: number;
  maximum?: number;
}

export interface OpenApiDoc {
  info: { title: string; description?: string };
  paths: Record<string, Record<string, OpenApiOperation>>;
  components?: { schemas?: Record<string, SchemaRef> };
}
