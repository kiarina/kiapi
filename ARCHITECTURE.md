# kiapi Architecture

**English** | [日本語](ARCHITECTURE.ja.md)

## Repository Structure

- The file structure follows Crystal Architecture.
  - [kiarina/crystal-architecture](https://github.com/kiarina/crystal-architecture)
- Configuration management uses Pydantic Settings Manager.
  - [kiarina/pydantic-settings-manager](https://github.com/kiarina/pydantic-settings-manager)

```sh
kiapi/
  core/                # capability-independent foundation
    app/               # app context, startup wiring, user-directory resolution
    model/             # model registry and ModelSpec catalog
    setup/             # setup status / activate / deactivate for resources
    memory/            # global memory-budget manager and TTL eviction
    worker/            # single-flight worker: one dedicated thread + queue
    job/               # unified job model and in-memory job store
    file/              # unified file store and file_id management
    workdir/           # temporary working directory management
    net/               # network guard for user-provided URLs
    logging/           # logging setup

  capabilities/        # one package per family (dir == family)
    chat/              # OpenAI-compatible chat completions (multimodal / tool / stream)
    embedding/         # multimodal embedding
    zimage/            # image generation (Z-Image, LoRA training)
    flux2/             # image generation and editing (FLUX.2 Klein)
    qwen/              # image generation and editing (Qwen Image)
    ideogram4/         # image generation (Ideogram 4, typography)
    ernie/             # image generation and editing (ERNIE-Image)
    seedvr2/           # image super-resolution (SeedVR2)
    depthpro/          # depth estimation (Depth Pro)
    acestep/           # music generation (ACE-Step 1.5, subprocess in a separate venv)
    audiogen/          # sound-effect generation (AudioGen)
    ltx2/              # video generation (LTX-2)
    web/               # web search/fetch (SearXNG + Crawl4AI resident subprocess)

  api/                 # FastAPI routers. Generation APIs are grouped by domain/family.
    chat/              # POST /v1/chat/completions
    embedding/         # POST /v1/embedding
    image/
      zimage/          # POST /v1/image/zimage/{generate,train}
      flux2/           # POST /v1/image/flux2/{generate,edit,train}
      qwen/            # POST /v1/image/qwen/{generate,edit}
      ideogram4/       # POST /v1/image/ideogram4/generate
      ernie/           # POST /v1/image/ernie/{generate,edit,train}
      seedvr2/         # POST /v1/image/seedvr2/upscale
      depthpro/        # POST /v1/image/depthpro/estimate
    audio/
      acestep/         # POST /v1/audio/acestep/{generate,cover,repaint,extract}
      audiogen/        # POST /v1/audio/audiogen/generate
    video/
      ltx2/            # POST /v1/video/ltx2/generate
    web/               # POST /v1/web/search, GET /v1/web/fetch
    files/             # POST/GET/DELETE /v1/files
    jobs/              # GET/DELETE /v1/jobs
    models/            # GET /v1/models, /v1/{domain}/{family}/models
    health/            # GET /health
    openapi            # GET /openapi.json, /v1/{domain}/{family}/openapi.json
```

## Startup Flow

```sh
app startup
  -> call register() for each capability
      -> register ModelSpec entries in the model registry
      -> register CapabilitySpec entries in the capability registry
  -> mount FastAPI routers
  -> warm up configured KIAPI_WARMUP_MODELS within the memory budget
  -> start accepting requests
```

Warmup is optional. Models that are not warmed up are loaded lazily on first
`acquire`. Warmup targets that have not been activated are skipped with a
warning, and server startup continues.

## App Settings and User Directories

`core/app` owns the application-wide `AppContext` and resolves user-specific
directories. Explicit settings win first, then XDG-style environment variables,
then `platformdirs`.

| Purpose | Setting | Environment fallback | platformdirs |
|---|---|---|---|
| cache | `KIAPI_USER_CACHE_DIR` | `XDG_CACHE_HOME/kiapi` | `PlatformDirs(appname="kiapi", appauthor="kiarina").user_cache_dir` |
| config | `KIAPI_USER_CONFIG_DIR` | `XDG_CONFIG_HOME/kiapi` | `PlatformDirs(appname="kiapi", appauthor="kiarina").user_config_dir` |
| data | `KIAPI_USER_DATA_DIR` | `XDG_DATA_HOME/kiapi` | `PlatformDirs(appname="kiapi", appauthor="kiarina").user_data_dir` |

`~` in configured paths is expanded for the current user.

## Setup Management

Model weights, Docker images, Python packages, and capability-specific virtual
environments are activated before serving so heavy downloads do not happen
during API requests.

| resource | status check | activate | deactivate |
|---|---|---|---|
| `hf_snapshot` | `snapshot_download(..., local_files_only=True)` succeeds | download from Hugging Face | remove the matching cache entry |
| `docker_image` | `docker image inspect` succeeds | `docker pull` | `docker image rm` |
| `local_path` | path exists | no-op | remove the path |
| `python_venv` | validation import succeeds with the venv Python | `uv venv` + `uv pip install` | remove the venv directory |

At request time, handlers call `ctx.ensure_model_ready(spec)`. Missing setup
raises `SetupRequiredError`, which routers convert into HTTP 503 with an
activation hint.

## Processing Flow

Requests are converted to jobs and submitted to the single-flight worker. GPU
models and resident subprocess capabilities use the same acquire/release path.

### Inference APIs (sync)

```sh
request
  -> api router validates the request and resolves parameters
  -> submit_and_maybe_wait
  -> worker, one job at a time
      -> memory.acquire(model)
      -> capability handler reports progress and produces output
      -> files.put(...) stores artifacts
  -> wait until completion or KIAPI_SYNC_TIMEOUT_S
  -> response: raw artifact bytes or Job JSON
```

### Inference APIs (async)

```sh
request with mode=async
  -> enqueue job
  -> return 202 + job_id
  -> client polls GET /v1/jobs/{id}
  -> client downloads artifacts through GET /v1/files/{id}/download
```

### Web API

Web search/fetch also runs through the worker. `memory.acquire` starts the
resident SearXNG or Crawl4AI Docker subprocess on first use, waits for its
healthcheck, and passes the local backend URL to the capability handler.

## Models

All servable models are registered as `ModelSpec` entries in one global model
registry.

| Field | Meaning |
|---|---|
| `name` / `aliases` | model variant identifiers accepted by the API |
| `family` / `domain` | routing and grouping keys |
| `modalities_in` | accepted input modalities |
| `weight_gb` / `peak_headroom_gb` | estimates used by memory accounting |
| `framework` | cleanup strategy, such as MLX, Torch/MPS, or subprocess |
| `resident` | whether the loaded payload remains resident after use |
| `ttl_seconds` | idle TTL; unset inherits the global default |
| `priority` / `default` | eviction priority and family default |

`resolve(family, model)` selects a family-local variant. If `model` is omitted,
the family default is used. Resident models stay loaded until TTL or eviction;
non-resident models reserve peak memory for one run and release immediately.

## Memory Management

All models share one global `KIAPI_MEMORY_LIMIT_GB` budget. If unset, kiapi uses
80% of installed memory as the effective startup budget.

Memory accounting separates resident weights from per-job peak headroom:

```text
sum(resident weights except this job's model)
  + this job's model weight
  + this job's peak headroom
  <= memory limit
```

If the budget is insufficient, residents are evicted by `(priority ascending,
last_used ascending)`. Release functions perform framework-specific cleanup,
including MLX cache clearing and Torch/MPS cache clearing where needed.

## TTL (Idle Auto-Release)

Each resident model may have an idle TTL. Unset values inherit
`KIAPI_DEFAULT_TTL_S`; `0` or negative values pin the model indefinitely.

Expired residents are released in two places:

1. During `acquire`, before budget checks.
2. During the background sweep controlled by `KIAPI_TTL_SWEEP_INTERVAL_S`.

Sweeps run on the same single worker thread to preserve MLX thread affinity and
serialize cleanup with generation. `GET /health` reports `idle_s`, `ttl_s`, and
`expires_in_s`.

## Jobs / Worker

All work runs through a global `ThreadPoolExecutor(max_workers=1)` and queue.
This keeps GPU work single-flight, preserves MLX thread affinity, and makes
memory accounting predictable. Users who need parallelism should run multiple
kiapi processes and split the memory budget between them.

- Sync and async generation are always represented as jobs.
- Async generation returns a `job_id` immediately.
- Sync generation waits for completion and returns an error on timeout.
- Chat and embedding do not expose async mode, though they are jobs internally.
- Streaming is available for chat only.
- `DELETE /v1/jobs/{id}` can remove queued jobs; running jobs cannot be
  interrupted reliably.

### Job Model

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

## Progress Reporting

Progress reporting uses an ambient `contextvar`. The worker binds a
`ProgressReporter` before executing a job, and capability code calls
`ProgressReporter.current().update(...)` or `.step(...)`. When no reporter is
bound, `current()` returns a silent no-op reporter, so handlers do not need
special branching.

Clients observe progress through `GET /v1/jobs/{id}`.

## File Management

The Files API stores uploads, generated artifacts, and downloaded URL/data URL
inputs under stable `file_id`s. Files are longer-lived than in-memory jobs:
jobs disappear on process restart, but stored files remain accessible while the
configured files root still contains them.

Defaults:

| Purpose | Setting | Default |
|---|---|---|
| generated artifacts and uploads | `KIAPI_FILES_ROOT` | `/tmp/kiapi/files` |
| request-time intermediate work | `KIAPI_TMP_ROOT` | `/tmp/kiapi/work` |

Long-term artifacts should use a persistent `KIAPI_FILES_ROOT`, such as
`~/.kiapi/files` or an external disk.

## Sync Response Negotiation

Generation sync responses return raw bytes by default when there is a single
artifact. This makes commands such as `curl -o out.png .../generate` work
directly.

- `X-Kiapi-File-Id` and `X-Kiapi-Job-Id` carry references to the stored file and
  job.
- `Accept: application/json`, multiple artifacts, and async responses return
  Job JSON instead.
- The shared implementation lives in `api/_helpers/submit_and_maybe_wait.py`.

## API Organization (domain / family / op)

Chat and embedding expose standard modality APIs:

- `POST /v1/chat/completions`
- `POST /v1/embedding`

Generation APIs are provider/family-oriented:

```text
POST /v1/<domain>/<family>/<op>
```

`domain` groups by modality, `family` is a normalized upstream package/model
token, and `op` is the operation vocabulary that family supports. Common
envelopes are shared across generation APIs, while payload schemas stay
family-specific.

## Resident Subprocess Model

Some capabilities keep a resident subprocess rather than an in-process Python
model object.

- `acestep` runs an ACE-Step worker in a dedicated Python venv.
- `web/search` runs a foreground `docker run --rm searxng/searxng` subprocess.
- `web/fetch` runs a foreground `docker run --rm unclecode/crawl4ai` subprocess.

Core treats each as a resident model payload with `load(spec)` and
`release(payload)` behavior. The subprocess implementation detail stays inside
the capability.

## Dependency Isolation (acestep venv split)

Most capabilities share the main kiapi venv, but ACE-Step requires
`transformers` 4.x while chat and embedding use libraries that require
`transformers` 5.x. To avoid an unsatisfiable environment, `acestep` runs in a
dedicated venv built by `kiapi activate --family acestep`.

The main process still manages ACE-Step through the same job, file, memory, TTL,
and single-flight systems. IPC is line-oriented JSON over stdin/stdout, with
generated files passed by filesystem path. See
[acestep/README.md](kiapi/capabilities/acestep/README.md) for details.

## OpenAPI

kiapi exposes two machine-readable documentation layers:

1. `GET /openapi.json` lists capabilities, common endpoints, and docs URLs.
2. `GET /v1/{domain}/{family}/openapi.json` describes the selected capability's
   actual operations, schemas, examples, and tips.

The root OpenAPI answers "what can this server do, and where should I look
next?" Capability OpenAPI documents "how do I call this operation?".

`CapabilitySpec.summary` should stay task-oriented and concise because agents
use it to map user intent to a capability.
