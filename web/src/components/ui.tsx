import type { ReactNode } from "react";

import { AuthError, downloadPath, type FileRecord, type Job } from "../api";
import { useCopy, useFileSrc } from "../hooks";
import { useToken } from "../session";
import { Icon } from "./Icon";

export function PageHead({
  eyebrow,
  title,
  sub,
  actions,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  sub?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="page-head">
      <div className="titles">
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1 className="page-title">{title}</h1>
        {sub && <div className="page-sub">{sub}</div>}
      </div>
      {actions}
    </header>
  );
}

export function Command({ text }: { text: string }) {
  const [copied, copy] = useCopy();
  return (
    <span className="cmd">
      <span className="prompt">$</span>
      <span className="text" title={text}>
        {text}
      </span>
      <button
        type="button"
        className="icon-btn"
        aria-label={copied === text ? "Copied" : "Copy command"}
        onClick={() => copy(text)}
      >
        <Icon name={copied === text ? "check" : "copy"} size={13} />
      </button>
    </span>
  );
}

export function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, copy] = useCopy();
  return (
    <button type="button" className="btn small" onClick={() => copy(text)}>
      <Icon name={copied === text ? "check" : "copy"} size={14} />
      {copied === text ? "Copied" : label}
    </button>
  );
}

export function ProgressBar({ value, thin }: { value: number | null; thin?: boolean }) {
  const cls = `bar${thin ? " thin" : ""}${value === null ? " indeterminate" : ""}`;
  return (
    <div
      className={cls}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value === null ? undefined : Math.round(value * 100)}
    >
      <span style={value === null ? undefined : { width: `${Math.round(value * 100)}%` }} />
    </div>
  );
}

const STATUS_BADGE: Record<string, string> = {
  queued: "muted",
  running: "accent",
  succeeded: "ok",
  failed: "fail",
  canceled: "muted",
};

export function JobStatusBadge({ status }: { status: Job["status"] }) {
  return (
    <span className={`badge ${STATUS_BADGE[status] ?? "muted"}`}>
      {status === "running" && <span className="dot run pulse" />}
      {status}
    </span>
  );
}

export function jobDot(status: Job["status"]): string {
  if (status === "succeeded") return "dot ok";
  if (status === "failed") return "dot fail";
  if (status === "running") return "dot run pulse";
  return "dot";
}

export function ErrorBox({ error }: { error: Error }) {
  if (error instanceof AuthError) {
    return <div className="error">This server needs an access token. Set it from the key button in the sidebar.</div>;
  }
  return <div className="error">{error.message}</div>;
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="empty">
      <div style={{ maxWidth: 220, margin: "0 auto 10px" }}>
        <ProgressBar value={null} thin />
      </div>
      {label}
    </div>
  );
}

export function mediaKind(contentType: string): "image" | "video" | "audio" | "doc" {
  if (contentType.startsWith("image/")) return "image";
  if (contentType.startsWith("video/")) return "video";
  if (contentType.startsWith("audio/")) return "audio";
  return "doc";
}

export function Thumb({ file }: { file: FileRecord }) {
  const token = useToken();
  const kind = mediaKind(file.content_type);
  const src = useFileSrc(kind === "image" || kind === "video" ? downloadPath(file.file_id) : null, token);
  if (kind === "image" && src) {
    return <img className="thumb" src={src} alt={String(file.meta.prompt ?? file.filename)} loading="lazy" />;
  }
  if (kind === "video" && src) {
    return <video className="thumb" src={src} muted playsInline preload="metadata" />;
  }
  return (
    <div className="thumb" aria-hidden="true">
      <Icon name={kind} size={28} />
    </div>
  );
}

export function MediaPreview({ file }: { file: FileRecord }) {
  const token = useToken();
  const kind = mediaKind(file.content_type);
  const src = useFileSrc(kind === "doc" ? null : downloadPath(file.file_id), token);
  if (kind === "doc" || !src) {
    return (
      <div className="stage">
        <div className="muted" style={{ display: "grid", placeItems: "center", gap: 8 }}>
          <Icon name={kind} size={40} />
          {file.content_type}
        </div>
      </div>
    );
  }
  return (
    <div className="stage">
      {kind === "image" && <img src={src} alt={String(file.meta.prompt ?? file.filename)} />}
      {kind === "video" && <video src={src} controls playsInline />}
      {kind === "audio" && <audio src={src} controls />}
    </div>
  );
}
