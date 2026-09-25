import { useState } from "react";

import { downloadPath, type FileRecord } from "../api";
import { Icon } from "../components/Icon";
import { CopyButton, ErrorBox, Loading, MediaPreview, PageHead, Thumb, mediaKind } from "../components/ui";
import { sortedFiles, useData } from "../data";
import { ago, bytes } from "../format";
import { useFileSrc, useNow } from "../hooks";
import { useToken } from "../session";

type Kind = "all" | "image" | "video" | "audio" | "doc";

const KINDS: [Kind, string][] = [
  ["all", "All"],
  ["image", "Images"],
  ["video", "Video"],
  ["audio", "Audio"],
  ["doc", "Other"],
];

export function Files() {
  const { files } = useData();
  const now = useNow(30000);
  const [kind, setKind] = useState<Kind>("all");
  const all = sortedFiles(files.data?.data);
  const list = all.filter((f) => kind === "all" || mediaKind(f.content_type) === kind);

  return (
    <>
      <PageHead
        title="Files"
        sub={<span>Uploaded inputs and generated artifacts. Files stay on disk across restarts.</span>}
      />
      <div className="chips" role="group" aria-label="Filter files">
        {KINDS.map(([key, label]) => {
          const n = key === "all" ? all.length : all.filter((f) => mediaKind(f.content_type) === key).length;
          return (
            <button
              key={key}
              type="button"
              className={`chip${kind === key ? " on" : ""}`}
              aria-pressed={kind === key}
              onClick={() => setKind(key)}
            >
              {label} {n}
            </button>
          );
        })}
      </div>
      {files.error && <ErrorBox error={files.error} />}
      {!files.data && files.loading && <Loading />}
      {files.data && list.length === 0 && <div className="card empty">No files here.</div>}
      <div className="gallery" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))" }}>
        {list.map((f) => (
          <a key={f.file_id} className="tile-media" href={`#/files/${f.file_id}`}>
            <Thumb file={f} />
            <span className="cap">
              <b>{f.filename}</b>
              <span>
                {bytes(f.size)} · {ago(f.created_at, now)}
              </span>
            </span>
          </a>
        ))}
      </div>
    </>
  );
}

function metaText(meta: Record<string, unknown>, key: string): string | undefined {
  const v = meta[key];
  if (typeof v === "string") return v;
  if (v && typeof v === "object") return JSON.stringify(v);
  return undefined;
}

export function FileDetail({ id }: { id: string }) {
  const { files } = useData();
  const token = useToken();
  const file: FileRecord | undefined = files.data?.data.find((f) => f.file_id === id);
  const downloadSrc = useFileSrc(file ? downloadPath(file.file_id) : null, token);
  const prompt = file ? metaText(file.meta, "prompt") : undefined;
  const { prompt: _p, params, ...restMeta } = file?.meta ?? {};

  return (
    <>
      <a href="#/files" className="small" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
        <Icon name="back" size={14} />
        Files
      </a>
      <PageHead
        eyebrow={<span className="mono">{id}</span>}
        title={file?.filename ?? "File"}
        actions={
          file && (
            <>
              <CopyButton text={file.file_id} label="Copy file id" />
              {downloadSrc && (
                <a className="btn small" href={downloadSrc} download={file.filename}>
                  <Icon name="download" size={14} />
                  Download
                </a>
              )}
            </>
          )
        }
      />
      {files.error && <ErrorBox error={files.error} />}
      {!file && files.loading && <Loading />}
      {!file && files.data && <div className="card empty">Unknown file.</div>}
      {file && (
        <div className="grid-aside">
          <div style={{ display: "flex", flexDirection: "column", gap: 20, minWidth: 0 }}>
            <MediaPreview file={file} />
            {prompt && (
              <div className="card">
                <h2 className="card-title">Prompt</h2>
                <div style={{ fontSize: 15, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{prompt}</div>
              </div>
            )}
            {params !== undefined && (
              <div className="card">
                <h2 className="card-title">Parameters</h2>
                <pre className="json">{JSON.stringify(params, null, 2)}</pre>
              </div>
            )}
          </div>
          <div className="card">
            <dl className="kv">
              <dt>Type</dt>
              <dd className="mono small">{file.content_type}</dd>
              <dt>Size</dt>
              <dd>{bytes(file.size)}</dd>
              <dt>Created</dt>
              <dd>{new Date(file.created_at * 1000).toLocaleString()}</dd>
              {Object.entries(restMeta).map(([k, v]) => (
                <FragmentKV key={k} k={k} v={v} />
              ))}
            </dl>
          </div>
        </div>
      )}
    </>
  );
}

function FragmentKV({ k, v }: { k: string; v: unknown }) {
  const text = typeof v === "object" && v !== null ? JSON.stringify(v) : String(v);
  return (
    <>
      <dt>{k}</dt>
      <dd className={typeof v === "object" ? "mono small" : undefined}>{text}</dd>
    </>
  );
}
