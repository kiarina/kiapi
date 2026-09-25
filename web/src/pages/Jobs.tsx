import type { FileRecord, Job } from "../api";
import { Icon } from "../components/Icon";
import { CopyButton, ErrorBox, JobStatusBadge, Loading, PageHead, ProgressBar, Thumb } from "../components/ui";
import { sortedJobs, useData } from "../data";
import { ago, duration, shortId } from "../format";
import { useApi, useNow } from "../hooks";

const COLUMNS = "130px 120px minmax(0, 1fr) 110px 80px 90px";

export function Jobs() {
  const { jobs } = useData();
  const now = useNow();
  const list = sortedJobs(jobs.data?.data);

  return (
    <>
      <PageHead
        title="Jobs"
        sub={<span>Every generation is a job. Jobs live in memory and are cleared when kiapi restarts.</span>}
      />
      {jobs.error && <ErrorBox error={jobs.error} />}
      {!jobs.data && jobs.loading && <Loading />}
      {jobs.data && list.length === 0 && (
        <div className="card empty">No jobs since the server started.</div>
      )}
      {list.length > 0 && (
        <div className="table">
          <div className="table-head hide-sm" style={{ gridTemplateColumns: COLUMNS }}>
            <span>Job</span>
            <span>Family</span>
            <span>Details</span>
            <span>Status</span>
            <span className="num">Took</span>
            <span style={{ textAlign: "right" }}>Created</span>
          </div>
          {list.map((j) => (
            <a key={j.id} href={`#/jobs/${j.id}`} className="table-row" style={{ gridTemplateColumns: COLUMNS }}>
              <span className="mono small hide-sm">{shortId(j.id)}</span>
              <span style={{ fontWeight: 500 }}>{j.type}</span>
              <span className="wide" style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                <span style={{ color: "var(--text-2)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {[j.params.model, j.params.kind, j.params.prompt].filter((v) => typeof v === "string").join(" · ")}
                </span>
                {j.status === "running" && <ProgressBar thin value={j.progress} />}
              </span>
              <span className="push">
                <JobStatusBadge status={j.status} />
              </span>
              <span className="num">
                {j.started_at ? duration((j.finished_at ?? now) - j.started_at) : "—"}
              </span>
              <span className="small muted" style={{ textAlign: "right" }}>
                {ago(j.created_at, now)}
              </span>
            </a>
          ))}
        </div>
      )}
    </>
  );
}

export function JobDetail({ id }: { id: string }) {
  const job = useApi<Job>(`/v1/jobs/${encodeURIComponent(id)}`, 1500);
  const { files } = useData();
  const now = useNow();
  const j = job.data;
  const artifacts: FileRecord[] = (j?.artifacts ?? [])
    .map((fid) => files.data?.data.find((f) => f.file_id === fid))
    .filter((f): f is FileRecord => Boolean(f));

  return (
    <>
      <a href="#/jobs" className="small" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
        <Icon name="back" size={14} />
        Jobs
      </a>
      <PageHead
        eyebrow={j ? <span className="mono">{j.id}</span> : undefined}
        title={j ? j.type : "Job"}
        actions={j && <CopyButton text={j.id} label="Copy job id" />}
      />
      {job.error && <ErrorBox error={job.error} />}
      {!j && job.loading && <Loading />}
      {j && (
        <div className="grid-aside">
          <div style={{ display: "flex", flexDirection: "column", gap: 20, minWidth: 0 }}>
            {(j.status === "running" || j.status === "queued") && (
              <div className="card">
                <div style={{ display: "flex" }} className="small">
                  <span style={{ flex: 1, color: "var(--text-2)" }}>
                    {j.status === "queued" ? "Waiting in the queue" : j.progress_label || "Working"}
                  </span>
                  <span className="mono">{j.progress === null ? "" : `${Math.round(j.progress * 100)}%`}</span>
                </div>
                <ProgressBar value={j.status === "queued" ? null : j.progress} />
              </div>
            )}
            {j.error && <div className="error">{j.error}</div>}
            {j.artifacts.length > 0 && (
              <div className="card">
                <h2 className="card-title">Artifacts</h2>
                <div className="gallery">
                  {artifacts.map((f) => (
                    <a key={f.file_id} className="tile-media" href={`#/files/${f.file_id}`}>
                      <Thumb file={f} />
                      <span className="cap">
                        <b>{f.filename}</b>
                        <span>{f.content_type}</span>
                      </span>
                    </a>
                  ))}
                  {artifacts.length < j.artifacts.length &&
                    j.artifacts
                      .filter((fid) => !artifacts.some((f) => f.file_id === fid))
                      .map((fid) => (
                        <a key={fid} className="mono small" href={`#/files/${fid}`}>
                          {shortId(fid)}
                        </a>
                      ))}
                </div>
              </div>
            )}
            <div className="card">
              <h2 className="card-title">Parameters</h2>
              <pre className="json">{JSON.stringify(j.params, null, 2)}</pre>
            </div>
            {j.result !== null && j.result !== undefined && (
              <div className="card">
                <h2 className="card-title">Result</h2>
                <pre className="json">{JSON.stringify(j.result, null, 2)}</pre>
              </div>
            )}
          </div>
          <div className="card">
            <dl className="kv">
              <dt>Status</dt>
              <dd>
                <JobStatusBadge status={j.status} />
              </dd>
              <dt>Family</dt>
              <dd>{j.type}</dd>
              {typeof j.params.model === "string" && (
                <>
                  <dt>Model</dt>
                  <dd className="mono">{j.params.model}</dd>
                </>
              )}
              <dt>Created</dt>
              <dd>{new Date(j.created_at * 1000).toLocaleString()}</dd>
              <dt>Waited</dt>
              <dd>{duration((j.started_at ?? now) - j.created_at)}</dd>
              <dt>Ran</dt>
              <dd>{j.started_at ? duration((j.finished_at ?? now) - j.started_at) : "—"}</dd>
            </dl>
          </div>
        </div>
      )}
    </>
  );
}
