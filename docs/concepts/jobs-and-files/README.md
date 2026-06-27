# Jobs and Files

**English** | [日本語](README.ja.md)

This concept describes request execution, serialization, progress reporting,
and artifact storage.

## Processing Flow

Capability requests become jobs submitted to one single-flight worker:

```text
request
  -> router validates input
  -> enqueue Job
  -> memory.acquire(model)
  -> capability handler reports progress and produces output
  -> files.put(...) stores artifacts
  -> return raw bytes or Job JSON
```

Synchronous generation waits up to `KIAPI_SYNC_TIMEOUT_S`. Asynchronous
generation returns HTTP 202 with a `job_id`; clients poll `/v1/jobs/{id}` and
download completed artifacts from the Files API. Chat and embedding are jobs
internally but do not expose async mode.

## Single-Flight Worker

All work runs through a global `ThreadPoolExecutor(max_workers=1)` and queue.
This preserves MLX thread affinity, keeps GPU work serial, and makes peak-memory
accounting deterministic. Parallel deployments use multiple kiapi processes
with separate memory budgets.

Queued jobs can be canceled. Running inference cannot be interrupted reliably.
Chat streaming still occupies the same worker while generation runs.

## Job Model

```text
Job:
  id: str
  type: str
  status: queued | running | succeeded | failed | canceled
  params: dict
  result: dict
  artifacts: [file_id]
  error: str | None
  created_at / started_at / finished_at
  progress: float | None
  progress_label: str | None
```

Jobs live in memory and disappear when the process restarts.

## Progress Reporting

The worker binds a `ProgressReporter` through a `contextvar` before executing a
job. Capability code calls `ProgressReporter.current().update(...)` or
`.step(...)`. Outside a job, `current()` returns a silent no-op reporter.

Clients observe the latest progress through `GET /v1/jobs/{id}`.

## File Lifecycle

The Files API stores uploads, generated artifacts, and expanded URL or data URL
inputs under stable `file_id`s. Files outlive in-memory jobs while their storage
root remains available.

| Purpose | Setting | Default |
|---|---|---|
| uploads and generated artifacts | `KIAPI_FILES_ROOT` | `/tmp/kiapi/files` |
| request-time intermediate work | `KIAPI_TMP_ROOT` | `/tmp/kiapi/work` |

Use a persistent `KIAPI_FILES_ROOT` for long-lived artifacts.

## Sync Response Negotiation

A synchronous generation response returns raw bytes by default when it has one
artifact. `X-Kiapi-File-Id` and `X-Kiapi-Job-Id` preserve references to the
stored file and job.

`Accept: application/json`, multiple artifacts, and asynchronous responses
return Job JSON instead.

## Related Concepts

- [Model Lifecycle](../model-lifecycle/)
- [API](../api/)
- [Architecture overview](../../../ARCHITECTURE.md)
