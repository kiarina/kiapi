import { useEffect, useMemo, useRef, useState } from "react";
import Markdown from "react-markdown";

import { apiFetch, downloadPath, postJson, type AsyncJob, type FileRecord, type Job, type OpenApiDoc, type SetupModel } from "../api";
import { Icon } from "../components/Icon";
import { CopyButton, ErrorBox, JobStatusBadge, MediaPreview, ProgressBar, Thumb } from "../components/ui";
import { sortedJobs, useData } from "../data";
import { duration } from "../format";
import { useApi, useFileSrc, useNow } from "../hooks";
import { useToken } from "../session";
import { FieldInput } from "./fields";
import { acceptFor } from "./FilePicker";
import { setFormBridge } from "./formBridge";
import { buildPayload, operationsOf, valuesFromParams, type Field, type Operation, type Values } from "./schema";
import { WriteWithChat } from "./WriteWithChat";

type Outcome =
  | { kind: "job"; jobId: string }
  | { kind: "json"; data: unknown }
  | { kind: "text"; text: string; contentType: string }
  | { kind: "blob"; url: string; contentType: string };

interface SearchOptions {
  categories: string[];
  engines: string[];
}

const TERMINAL = new Set(["succeeded", "failed", "canceled"]);
// Fields a chat model can write from the family guide.
const WRITABLE = new Set(["prompt", "negative_prompt", "lyrics"]);

function takesImage(f: Field): boolean {
  return (f.kind === "file" || f.kind === "files") && acceptFor(f.name) === "image";
}

export function belongsTo(job: Job, family: string): boolean {
  return job.type === family || job.type.startsWith(`${family}-`);
}

export function Playground({
  doc,
  family,
  models,
}: {
  doc: OpenApiDoc;
  family: string;
  models: SetupModel[];
}) {
  const searchOptions = useApi<SearchOptions>(family === "web" ? "/v1/web/search/options" : null);
  const ops = useMemo(() => operationsOf(doc).map((op) => ({
    ...op,
    fields: op.fields.map((field) => {
      if (family !== "web" || op.name !== "search") return field;
      if (field.name === "categories") return { ...field, options: searchOptions.data?.categories ?? [] };
      if (field.name === "engines") return { ...field, options: searchOptions.data?.engines ?? [] };
      return field;
    }),
  })), [doc, family, searchOptions.data]);
  const [opIndex, setOpIndex] = useState(0);
  const [valuesByOp, setValuesByOp] = useState<Record<string, Values>>({});
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [writing, setWriting] = useState<Field | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<Error>();
  const [outcome, setOutcome] = useState<Outcome>();
  const [flash, setFlash] = useState<Set<string>>(new Set());
  const formRef = useRef<HTMLFormElement>(null);
  const { jobs } = useData();

  useEffect(() => {
    setFormBridge({
      family,
      operations: ops,
      current: ops[opIndex]?.name ?? "",
      models: models.filter((m) => m.status !== "missing").map((m) => m.name),
      apply: (name, filled) => {
        const index = ops.findIndex((o) => o.name === name);
        if (index === -1) return;
        setOpIndex(index);
        setValuesByOp((s) => ({ ...s, [ops[index].path]: { ...(s[ops[index].path] ?? {}), ...filled } }));
        if (ops[index].fields.some((f) => f.advanced && f.name in filled)) setShowAdvanced(true);
        setFlash(new Set(Object.keys(filled)));
        window.setTimeout(() => setFlash(new Set()), 2400);
      },
    });
    return () => setFormBridge(null);
  }, [family, ops, opIndex, models]);

  const op: Operation | undefined = ops[opIndex];
  const values = (op && valuesByOp[op.path]) ?? {};
  const setValue = (name: string, v: unknown) =>
    op && setValuesByOp((s) => ({ ...s, [op.path]: { ...(s[op.path] ?? {}), [name]: v } }));

  // Model first, then the inputs being edited, then the prompt and the rest.
  const rank = (f: Field) => (f.kind === "model" ? 0 : f.kind === "file" || f.kind === "files" ? 1 : 2);
  const basic = (op?.fields.filter((f) => !f.advanced) ?? []).sort((a, b) => rank(a) - rank(b));
  const advanced = op?.fields.filter((f) => f.advanced) ?? [];
  const missingRequired = op?.fields.filter((f) => f.required && (values[f.name] === undefined || values[f.name] === "")) ?? [];
  const history = sortedJobs(jobs.data?.data).filter((j) => belongsTo(j, family)).slice(0, 12);
  const busy = jobs.data?.data.filter((j) => j.status === "running" || j.status === "queued").length ?? 0;
  const busyText = busy === 1 ? "1 job is running or waiting" : `${busy} jobs are running or waiting`;

  const submit = async () => {
    if (!op || missingRequired.length) return;
    setSubmitting(true);
    setError(undefined);
    try {
      const payload = buildPayload(op, values);
      if (op.method === "get") {
        const qs = new URLSearchParams(Object.entries(payload).map(([k, v]) => [k, String(v)]));
        const res = await apiFetch(`${op.path}?${qs}`);
        const ct = res.headers.get("content-type") ?? "";
        if (ct.includes("json")) setOutcome({ kind: "json", data: await res.json() });
        else if (ct.startsWith("text/")) setOutcome({ kind: "text", text: await res.text(), contentType: ct });
        else setOutcome({ kind: "blob", url: URL.createObjectURL(await res.blob()), contentType: ct });
      } else if (op.async) {
        const job = await postJson<AsyncJob>(op.path, payload);
        setOutcome({ kind: "job", jobId: job.job_id });
        jobs.reload();
      } else {
        setOutcome({ kind: "json", data: await postJson(op.path, payload) });
      }
    } catch (e) {
      setError(e as Error);
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && !writing) void submit();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const reuse = (job: Job) => {
    const target = ops.findIndex((o) => job.type === family ? o.name === ops[0].name : job.type.endsWith(`-${o.name}`));
    const index = target === -1 ? opIndex : target;
    setOpIndex(index);
    setValuesByOp((s) => ({ ...s, [ops[index].path]: valuesFromParams(ops[index], job.params) }));
  };

  const useAsInput = (fileId: string) => {
    // Prefer an operation that takes images, e.g. flux2 generate -> edit.
    const candidates = [opIndex, ...ops.keys()];
    for (const i of candidates) {
      const f = ops[i]?.fields.find(takesImage);
      if (!f) continue;
      setOpIndex(i);
      setValuesByOp((s) => {
        const cur = s[ops[i].path] ?? {};
        const next = f.kind === "files" ? [...((cur[f.name] as string[]) ?? []), fileId] : fileId;
        return { ...s, [ops[i].path]: { ...cur, [f.name]: next } };
      });
      return;
    }
  };

  const useInFetch = (url: string) => {
    const fetchIndex = ops.findIndex((operation) => operation.name === "fetch" && operation.fields.some((field) => field.name === "url"));
    if (fetchIndex === -1) return;
    const fetchPath = ops[fetchIndex].path;
    setValuesByOp((current) => ({ ...current, [fetchPath]: { ...(current[fetchPath] ?? {}), url } }));
    setOpIndex(fetchIndex);
    setFlash(new Set(["url"]));
    window.setTimeout(() => setFlash(new Set()), 2400);
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  if (!op) return <div className="card empty">This family has no operations to run from the UI.</div>;
  const canUseAsInput = ops.some((o) => o.fields.some(takesImage));

  return (
    <div className="playground">
      <form
        ref={formRef}
        className="pg-form"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        {ops.length > 1 && (
          <div className="seg wide" role="tablist" aria-label="Operation">
            {ops.map((o, i) => (
              <button
                key={o.path}
                type="button"
                role="tab"
                aria-selected={i === opIndex}
                className={i === opIndex ? "on" : ""}
                onClick={() => setOpIndex(i)}
              >
                {o.name}
              </button>
            ))}
          </div>
        )}
        {op.description && <p className="small muted" style={{ margin: 0 }}>{op.description.split(/\n\s*\n/)[0]}</p>}
        {family === "web" && op.name === "search" && searchOptions.error && (
          <p className="small muted" role="alert">Could not load search choices: {searchOptions.error.message}</p>
        )}

        {basic.map((f) => (
          <FieldInput
            key={f.name}
            flash={flash.has(f.name)}
            field={f}
            value={values[f.name]}
            onChange={(v) => setValue(f.name, v)}
            ctx={{ models, onWrite: WRITABLE.has(f.name) ? setWriting : undefined }}
          />
        ))}

        {advanced.length > 0 && (
          <>
            <button type="button" className="adv-toggle" aria-expanded={showAdvanced} onClick={() => setShowAdvanced((s) => !s)}>
              <Icon name={showAdvanced ? "chevronDown" : "chevronRight"} size={14} />
              Advanced · {advanced.map((f) => f.name).slice(0, 4).join(", ")}
              {advanced.length > 4 ? ` +${advanced.length - 4}` : ""}
            </button>
            {showAdvanced &&
              advanced.map((f) => (
                <FieldInput
                  key={f.name}
                  flash={flash.has(f.name)}
                  field={f}
                  value={values[f.name]}
                  onChange={(v) => setValue(f.name, v)}
                  ctx={{ models, onWrite: WRITABLE.has(f.name) ? setWriting : undefined }}
                />
              ))}
          </>
        )}

        <div className="pg-submit">
          <button type="submit" className="btn primary big" disabled={submitting || missingRequired.length > 0}>
            {submitting ? "Sending…" : op.name === family ? "Run" : op.name.charAt(0).toUpperCase() + op.name.slice(1)}
            <span className="kbd">⌘↵</span>
          </button>
          <div className="small muted" style={{ textAlign: "center" }}>
            {missingRequired.length > 0
              ? `Fill in ${missingRequired.map((f) => f.label.toLowerCase()).join(", ")}`
              : op.async
                ? busy > 0
                  ? `${busyText}; new jobs run in order`
                  : "Runs as a job; you can leave this page"
                : "Runs right away"}
          </div>
          <button type="button" className="adv-toggle" style={{ alignSelf: "center" }} onClick={() => setValuesByOp((s) => ({ ...s, [op.path]: {} }))}>
            Reset form
          </button>
        </div>
      </form>

      <section className="pg-result" aria-label="Result">
        {error && <ErrorBox error={error} />}
        {!outcome && !error && <EmptyResult family={family} />}
        {outcome?.kind === "job" && (
          <JobResult jobId={outcome.jobId} onReuse={reuse} onUseAsInput={canUseAsInput ? useAsInput : undefined} />
        )}
        {outcome && outcome.kind !== "job" && (
          <SyncResult outcome={outcome} onFetchUrl={family === "web" ? useInFetch : undefined} />
        )}

        {history.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div className="small muted" style={{ fontWeight: 500 }}>
              Recent {family} jobs
            </div>
            <div className="history">
              {history.map((j) => (
                <HistoryItem
                  key={j.id}
                  job={j}
                  selected={outcome?.kind === "job" && outcome.jobId === j.id}
                  onClick={() => setOutcome({ kind: "job", jobId: j.id })}
                />
              ))}
            </div>
          </div>
        )}
      </section>

      {writing && (
        <WriteWithChat
          doc={doc}
          family={family}
          op={op}
          field={writing}
          current={String(values[writing.name] ?? "")}
          onUse={(text) => {
            setValue(writing.name, text);
            setWriting(null);
          }}
          onClose={() => setWriting(null)}
        />
      )}
    </div>
  );
}

function EmptyResult({ family }: { family: string }) {
  return (
    <div className="stage" style={{ minHeight: 420 }}>
      <div className="muted" style={{ textAlign: "center", display: "grid", gap: 8, justifyItems: "center" }}>
        <Icon name="play" size={28} />
        <div>Fill in the form and run {family}.</div>
        <div className="small">Results appear here and in Jobs.</div>
      </div>
    </div>
  );
}

function HistoryItem({ job, selected, onClick }: { job: Job; selected: boolean; onClick: () => void }) {
  const { files } = useData();
  const file = files.data?.data.find((f) => f.file_id === job.artifacts[0]);
  return (
    <button type="button" className={`history-item${selected ? " on" : ""}`} onClick={onClick} title={String(job.params.prompt ?? job.type)}>
      {file ? (
        <Thumb file={file} />
      ) : (
        <span className="thumb">
          {job.status === "running" || job.status === "queued" ? (
            <span className="dot run pulse" />
          ) : (
            <JobStatusBadge status={job.status} />
          )}
        </span>
      )}
    </button>
  );
}

function ArtifactView({ fileId }: { fileId: string }) {
  const file = useApi<FileRecord>(`/v1/files/${fileId}`);
  if (!file.data) return <div className="stage" style={{ minHeight: 360 }} />;
  return <MediaPreview file={file.data} />;
}

function JobResult({
  jobId,
  onReuse,
  onUseAsInput,
}: {
  jobId: string;
  onReuse: (job: Job) => void;
  onUseAsInput?: (fileId: string) => void;
}) {
  const [done, setDone] = useState(false);
  const job = useApi<Job>(`/v1/jobs/${jobId}`, done ? undefined : 1000);
  const { files } = useData();
  const token = useToken();
  const now = useNow();
  const j = job.data;
  const first = j?.artifacts[0];
  const downloadSrc = useFileSrc(first ? downloadPath(first) : null, token);

  useEffect(() => {
    setDone(false);
  }, [jobId]);
  useEffect(() => {
    if (j && TERMINAL.has(j.status) && !done) {
      setDone(true);
      files.reload();
    }
  }, [j, done, files]);

  if (job.error) return <ErrorBox error={job.error} />;
  if (!j) return <div className="stage" style={{ minHeight: 420 }} />;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {j.status === "succeeded" && j.artifacts.length > 0 ? (
        j.artifacts.map((id) => <ArtifactView key={id} fileId={id} />)
      ) : j.status === "failed" || j.status === "canceled" ? (
        <div className="error">{j.error ?? `Job ${j.status}.`}</div>
      ) : j.status === "succeeded" ? (
        <pre className="json">{JSON.stringify(j.result, null, 2)}</pre>
      ) : (
        <div className="stage waiting" style={{ minHeight: 420 }}>
          <div style={{ width: "min(420px, 90%)", display: "grid", gap: 10 }}>
            <div style={{ display: "flex" }} className="small">
              <span style={{ flex: 1, color: "var(--text-2)" }}>
                {j.status === "queued" ? "Waiting in the queue" : j.progress_label || "Working"}
              </span>
              <span className="mono">{j.progress === null ? "" : `${Math.round(j.progress * 100)}%`}</span>
            </div>
            <ProgressBar value={j.status === "queued" ? null : j.progress} />
            <div className="small muted">
              {duration(now - (j.started_at ?? j.created_at))} {j.status === "queued" ? "waiting" : "elapsed"}
            </div>
          </div>
        </div>
      )}

      <div className="pg-actions">
        <div className="chips" style={{ flex: 1 }}>
          <JobStatusBadge status={j.status} />
          {typeof j.params.model === "string" && <span className="tag mono">{j.params.model}</span>}
          {typeof j.params.seed === "number" && <span className="tag mono">seed {j.params.seed}</span>}
          {j.started_at && j.finished_at && <span className="tag mono">{duration(j.finished_at - j.started_at)}</span>}
        </div>
        {onUseAsInput && first && j.status === "succeeded" && (
          <button type="button" className="btn small" onClick={() => onUseAsInput(first)}>
            Use as input
          </button>
        )}
        <button type="button" className="btn small" onClick={() => onReuse(j)}>
          Reuse settings
        </button>
        {downloadSrc && (
          <a className="btn small" href={downloadSrc} download aria-label="Download">
            <Icon name="download" size={14} />
          </a>
        )}
        <a className="btn small" href={`#/jobs/${j.id}`}>
          Details
        </a>
      </div>
    </div>
  );
}

interface SearchResult {
  title?: string;
  url?: string;
  content?: string;
  category?: string;
  img_src?: string;
  thumbnail?: string;
  thumbnail_src?: string;
  iframe_src?: string;
}

function httpUrl(value: string | undefined): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : undefined;
  } catch {
    return undefined;
  }
}

function videoEmbedUrl(value: string | undefined): string | undefined {
  const src = httpUrl(value);
  if (!src) return undefined;
  const url = new URL(src);
  if (url.protocol !== "https:") return undefined;
  if (["www.youtube-nocookie.com", "www.youtube.com"].includes(url.hostname) && /^\/embed\/[\w-]+\/?$/.test(url.pathname)) return src;
  if (url.hostname === "player.vimeo.com" && /^\/video\/\d+\/?$/.test(url.pathname)) return src;
  if (url.hostname === "www.dailymotion.com" && /^\/embed\/video\/[\w-]+\/?$/.test(url.pathname)) return src;
  return undefined;
}

function SearchPreview({ result }: { result: SearchResult }) {
  const [playing, setPlaying] = useState(false);
  const [posterIndex, setPosterIndex] = useState(0);
  const posters = [...new Set([result.thumbnail_src, result.thumbnail, result.img_src].map(httpUrl).filter((url): url is string => !!url))];
  const poster = posters[posterIndex];
  const image = poster && <img src={poster} alt={result.category === "images" ? result.title ?? "Search result image" : ""} loading="lazy" referrerPolicy="no-referrer" onError={() => setPosterIndex((index) => index + 1)} />;
  if (result.category === "images") {
    if (!poster) return null;
    return (
      <a className="search-preview" href={httpUrl(result.img_src) ?? httpUrl(result.url)} target="_blank" rel="noreferrer" aria-label={`Open image: ${result.title ?? "search result"}`}>
        {image}
      </a>
    );
  }
  if (result.category !== "videos") return null;
  const embed = videoEmbedUrl(result.iframe_src);
  if (playing && embed) {
    return <iframe className="search-preview search-video" src={embed} title={result.title ?? "Search result video"} allow="autoplay; encrypted-media; fullscreen; picture-in-picture" allowFullScreen referrerPolicy="strict-origin-when-cross-origin" />;
  }
  if (!poster && !embed) return null;
  const preview = <>{image}<span className="search-play"><Icon name="play" size={22} /></span></>;
  return embed ? (
    <button type="button" className="search-preview search-video" onClick={() => setPlaying(true)} aria-label={`Play video: ${result.title ?? "search result"}`}>
      {preview}
    </button>
  ) : (
    <a className="search-preview search-video" href={httpUrl(result.url)} target="_blank" rel="noreferrer" aria-label={`Open video: ${result.title ?? "search result"}`}>
      {preview}
    </a>
  );
}

function SyncResult({ outcome, onFetchUrl }: { outcome: Exclude<Outcome, { kind: "job" }>; onFetchUrl?: (url: string) => void }) {
  if (outcome.kind === "text") {
    return (
      <div className="card prose" style={{ maxHeight: "70vh", overflow: "auto" }}>
        {outcome.contentType.includes("markdown") ? <Markdown>{outcome.text}</Markdown> : <pre>{outcome.text}</pre>}
      </div>
    );
  }
  if (outcome.kind === "blob") {
    return (
      <div className="card">
        <a className="btn" href={outcome.url} download>
          <Icon name="download" size={15} />
          Download {outcome.contentType}
        </a>
      </div>
    );
  }
  const data = outcome.data as Record<string, unknown>;
  const results = Array.isArray(data?.results) ? (data.results as SearchResult[]) : null;
  const imageResults = results?.length && results.every((result) => result.category === "images");
  const embedding = Array.isArray(data?.embedding) ? (data.embedding as number[]) : undefined;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {results && (
        <div className="card">
          <h2 className="card-title">{results.length} results</h2>
          <div className={imageResults ? "search-image-grid" : "rows"}>
            {results.map((r, i) => (
              <div key={`${r.category}:${r.url}:${i}`} className="row search-result">
                <SearchPreview result={r} />
                {httpUrl(r.url) ? (
                  <a href={r.url} target="_blank" rel="noreferrer" style={{ fontWeight: 500, overflowWrap: "anywhere" }}>{r.title ?? r.url}</a>
                ) : <span style={{ fontWeight: 500 }}>{r.title ?? r.url}</span>}
                <span className="mono small muted" style={{ overflowWrap: "anywhere" }}>{r.url}</span>
                {r.content && <span className="small">{r.content}</span>}
                {r.url && /^https?:\/\//i.test(r.url) && onFetchUrl && (
                  <button type="button" className="btn small" style={{ alignSelf: "flex-start", marginTop: 6 }} onClick={() => onFetchUrl(r.url!)}>
                    Use in Fetch
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      {embedding && (
        <div className="card">
          <h2 className="card-title">{embedding.length}-dimensional embedding</h2>
          <div className="spark" aria-hidden="true">
            {embedding.slice(0, 96).map((v, i) => (
              <span key={i} style={{ height: `${Math.min(100, Math.abs(v) * 900)}%`, opacity: v < 0 ? 0.45 : 1 }} />
            ))}
          </div>
          <div>
            <CopyButton text={JSON.stringify(embedding)} label="Copy vector" />
          </div>
        </div>
      )}
      <details className="card" open={!results && !embedding}>
        <summary className="small" style={{ cursor: "pointer", fontWeight: 500 }}>
          Response JSON
        </summary>
        <pre className="json">{JSON.stringify(outcome.data, null, 2)}</pre>
      </details>
    </div>
  );
}
