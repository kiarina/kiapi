import { useMemo } from "react";

import { Icon } from "../components/Icon";
import { ErrorBox, PageHead, ProgressBar, Thumb, jobDot } from "../components/ui";
import { sortedFiles, sortedJobs, useData } from "../data";
import { groupFamilies } from "../families";
import { ago, duration, gb } from "../format";
import { useNow } from "../hooks";

export function Overview() {
  const { health, setup, jobs, files } = useData();
  const now = useNow();
  const all = sortedJobs(jobs.data?.data);
  const running = all.filter((j) => j.status === "running");
  const queued = all.filter((j) => j.status === "queued").reverse();
  const recent = all.filter((j) => j.status !== "running" && j.status !== "queued").slice(0, 6);
  const recentFiles = sortedFiles(files.data?.data).slice(0, 12);
  const groups = useMemo(() => groupFamilies(setup.data?.data ?? []), [setup.data]);
  const familyCount = groups.reduce((n, g) => n + g.families.length, 0);
  const mem = health.data?.memory;
  const summary = setup.data?.summary;

  return (
    <>
      <PageHead
        title="Overview"
        sub={
          <>
            {familyCount > 0 && (
              <>
                <span>
                  {familyCount} families across {groups.length} domains
                </span>
                <span className="sep" />
              </>
            )}
            {mem && (
              <>
                <span>Memory budget {gb(mem.budget_gb)}</span>
                <span className="sep" />
              </>
            )}
            <span>
              Edit settings with <code className="inline-code">kiapi config edit</code>
            </span>
          </>
        }
        actions={
          <button
            type="button"
            className="btn"
            onClick={() => {
              health.reload();
              jobs.reload();
              files.reload();
              setup.reload();
            }}
          >
            <Icon name="refresh" size={15} />
            Refresh
          </button>
        }
      />

      {health.error && <ErrorBox error={health.error} />}

      <section className="grid-4" aria-label="Status">
        <div className="card tile">
          <div className="tile-label">
            <span>Server</span>
          </div>
          <div className="tile-value">
            <span className={`dot big ring ${health.data?.warm ? "ok" : "warn pulse"}`} />
            {health.data ? (health.data.warm ? "Warm" : "Warming up") : "—"}
          </div>
          <div className="tile-foot">
            {health.data?.warm ? "Warmup complete, accepting requests" : "Loading configured models"}
          </div>
        </div>
        <div className="card tile">
          <div className="tile-label">
            <span>Queue</span>
          </div>
          <div className="tile-value">
            {running.length}
            <small>running</small>
            <span style={{ marginLeft: 8 }}>{health.data?.queue_len ?? queued.length}</span>
            <small>waiting</small>
          </div>
          <div className="tile-foot">One job at a time, in order</div>
        </div>
        <div className="card tile">
          <div className="tile-label">
            <span>Memory</span>
            <span className="mono" style={{ fontWeight: 400 }}>
              {gb(mem?.budget_gb)}
            </span>
          </div>
          <div className="tile-value">
            {mem ? mem.resident_gb.toFixed(1) : "—"}
            <small>GB resident</small>
          </div>
          <ProgressBar thin value={mem ? Math.min(1, mem.resident_gb / mem.budget_gb) : 0} />
        </div>
        <a className="card tile" href="#/models">
          <div className="tile-label">
            <span>Setup</span>
            <span style={{ color: "var(--accent)" }}>View models</span>
          </div>
          <div className="tile-value">
            {summary ? summary.models_ready : "—"}
            <small>of {summary?.models_total ?? "…"} models ready</small>
          </div>
          <div className="tile-foot">
            {summary
              ? `${gb(summary.installed_gb)} installed · ${summary.models_total - summary.models_ready} not set up`
              : setup.loading
                ? "Checking resources…"
                : "—"}
          </div>
        </a>
      </section>

      <section className="grid-split">
        <div className="card">
          <div className="card-head">
            <h2 className="card-title">Now running</h2>
            <a href="#/jobs" className="small">
              All jobs
            </a>
          </div>
          {running.length === 0 && <div className="empty">Nothing is running.</div>}
          {running.map((j) => (
            <a key={j.id} href={`#/jobs/${j.id}`} className="op" style={{ color: "var(--text)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="badge accent">{j.type}</span>
                {typeof j.params.model === "string" && <span className="mono small muted">{j.params.model}</span>}
                <span className="grow" />
              </div>
              {typeof j.params.prompt === "string" && (
                <div style={{ fontSize: 15, lineHeight: 1.5 }}>{j.params.prompt}</div>
              )}
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ display: "flex" }} className="small">
                  <span style={{ flex: 1, color: "var(--text-2)" }}>{j.progress_label || "Working"}</span>
                  <span className="mono">{j.progress === null ? "" : `${Math.round(j.progress * 100)}%`}</span>
                </div>
                <ProgressBar value={j.progress} />
                <div className="small muted">
                  Started {duration(now - (j.started_at ?? j.created_at))} ago
                </div>
              </div>
            </a>
          ))}
          {queued.length > 0 && (
            <div className="rows" style={{ borderTop: "1px solid var(--line-soft)" }}>
              <div className="small muted" style={{ padding: "12px 0 4px", fontWeight: 500 }}>
                Waiting
              </div>
              {queued.map((j, i) => (
                <a key={j.id} href={`#/jobs/${j.id}`} className="row">
                  <span className="mono small muted" style={{ width: 16 }}>
                    {i + 1}
                  </span>
                  <span style={{ fontWeight: 500, width: 110 }}>{j.type}</span>
                  <span className="grow">{String(j.params.prompt ?? "")}</span>
                  <span className="mono small muted">{String(j.params.model ?? "")}</span>
                </a>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-head">
            <h2 className="card-title">Recent jobs</h2>
            <a href="#/jobs" className="small">
              All jobs
            </a>
          </div>
          {jobs.error && <ErrorBox error={jobs.error} />}
          {recent.length === 0 && !jobs.error && (
            <div className="empty">No finished jobs since the server started.</div>
          )}
          <div className="rows">
            {recent.map((j) => (
              <a key={j.id} href={`#/jobs/${j.id}`} className="row">
                <span className={jobDot(j.status)} />
                <span style={{ fontWeight: 500, width: 96 }}>{j.type}</span>
                <span className="grow">{String(j.params.model ?? j.params.kind ?? "")}</span>
                <span className="mono small muted" style={{ width: 60, textAlign: "right" }}>
                  {j.started_at && j.finished_at ? duration(j.finished_at - j.started_at) : "—"}
                </span>
                <span className="small muted" style={{ width: 64, textAlign: "right" }}>
                  {ago(j.created_at, now)}
                </span>
              </a>
            ))}
          </div>
        </div>
      </section>

      <section style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="card-head">
          <h2 className="card-title">Recent files</h2>
          {files.data && (
            <a href="#/files" className="small">
              All {files.data.data.length} files
            </a>
          )}
        </div>
        {recentFiles.length === 0 && !files.loading && <div className="empty">No files yet.</div>}
        <div className="gallery">
          {recentFiles.map((f) => (
            <a key={f.file_id} className="tile-media" href={`#/files/${f.file_id}`}>
              <Thumb file={f} />
              <span className="cap">
                <b>{f.filename}</b>
                <span>{String(f.meta.model ?? f.content_type)}</span>
              </span>
            </a>
          ))}
        </div>
      </section>
    </>
  );
}
