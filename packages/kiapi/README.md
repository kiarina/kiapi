# kiapi

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Apple%20Silicon-lightgrey.svg)
[![API Docs](https://img.shields.io/badge/API%20Docs-GitHub%20Pages-green.svg)](https://kiarina.github.io/kiapi/)

**English** | [日本語](README.ja.md)

## Summary

kiapi is a local API server that uses Apple Silicon and MLX to provide generative AI capabilities for LLM agents.

## API

| Domain | Family | Endpoint | Description |
|---|---|---|---|
| chat |  | `POST /v1/chat` | [Chat API details](./kiapi/capabilities/chat/README.md) |
| embedding |  | `POST /v1/embedding` | [Embedding API details](./kiapi/capabilities/embedding/README.md) |
| image | zimage | `POST /v1/image/zimage` | [Z-Image API details](./kiapi/capabilities/zimage/README.md) |
|  | flux2 | `POST /v1/image/flux2` | [FLUX.2 API details](./kiapi/capabilities/flux2/README.md) |
|  | qwen | `POST /v1/image/qwen` | [Qwen Image API details](./kiapi/capabilities/qwen/README.md) |
|  | ideogram4 | `POST /v1/image/ideogram4` | [Ideogram 4 API details](./kiapi/capabilities/ideogram4/README.md) |
|  | ernie | `POST /v1/image/ernie` | [ERNIE-Image API details](./kiapi/capabilities/ernie/README.md) |
|  | seedvr2 | `POST /v1/image/seedvr2` | [SeedVR2 API details](./kiapi/capabilities/seedvr2/README.md) |
|  | depthpro | `POST /v1/image/depthpro` | [Depth Pro API details](./kiapi/capabilities/depthpro/README.md) |
| audio | acestep | `POST /v1/audio/acestep` | [ACE-Step API details](./kiapi/capabilities/acestep/README.md) |
|  | audiogen | `POST /v1/audio/audiogen` | [AudioGen API details](./kiapi/capabilities/audiogen/README.md) |
| video | ltx2 | `POST /v1/video/ltx2` | [LTX-2 API details](./kiapi/capabilities/ltx2/README.md) |
| web |  | `POST /v1/web` | [Web API details](./kiapi/capabilities/web/README.md) |
| core | files | `POST /v1/files` | Upload input files, LoRA adapters, and other files, then issue a `file_id`. |
|  |  | `GET /v1/files` | Return a list of stored files. |
|  |  | `GET /v1/files/{file_id}` | Return file metadata. |
|  |  | `GET /v1/files/{file_id}/download` | Download the file body. |
|  |  | `DELETE /v1/files/{file_id}` | Delete a stored file. |
|  | jobs | `GET /v1/jobs` | Return a list of generation jobs. |
|  |  | `GET /v1/jobs/{job_id}` | Return job status, progress, result, and artifact `file_id`s. |
|  |  | `DELETE /v1/jobs/{job_id}` | Remove a job from the job store. Running jobs are not interrupted. |
|  | openapi | `GET /openapi.json` | Return the common API and each capability documentation URL. |
|  |  | `GET /v1/{domain}/{family}/openapi.json` | Return detailed input/output specs, usage, tips, and examples for each family. |
|  | health | `GET /health` | Return server status, warmup status, queue length, and memory usage. |

See: [kiapi API Docs](https://kiarina.github.io/kiapi/)

## Requirements

- macOS / Apple Silicon
- Python `>=3.12,<3.13`
- `uv` (optional, recommended for isolated CLI installs and faster venv/package setup in `kiapi activate`)
- `mise` (used for development)
- Docker (when using the Web capability)
- Enough disk capacity for model weights and Docker images

kiapi is developed mainly for personal use on a **Mac Studio M4 Max 128GB**.
Some or all features may work on other Apple Silicon environments, but they are
not the primary verification target.

The memory budget can be specified with `KIAPI_MEMORY_LIMIT_GB`. If omitted,
kiapi automatically uses 80% of installed memory as the effective budget on
startup. If a model's required memory does not fit in that budget, requests
return 503 as an insufficient memory budget error.

`kiapi activate --all` uses a little under 600GB of disk capacity, including
model weights and Docker images. At first, it is recommended to use `kiapi activate`
to set up only the capabilities you need.

## Remote Job Relay

The optional GCP relay lets a kiapi node inside a closed network receive API
work without exposing an inbound socket. Firebase Realtime Database carries
small notifications, while Cloud Storage carries request and response bodies.
Install kiapi with the `relay-gcp` extra to enable it:

```sh
python3.12 -m pip install --upgrade "kiapi[relay-gcp]"
uv tool install --python 3.12 "kiapi[relay-gcp]"
```

```sh
export KIAPI_RELAY_GCP_NODE_ID="studio-1"
export KIAPI_RELAY_GCP_DATABASE_URL="https://PROJECT.firebaseio.com"
export KIAPI_RELAY_GCP_BUCKET="PRIVATE_RELAY_BUCKET"
export KIAPI_RELAY_GCP_PREFIX="private/kiapi"

# Uses Application Default Credentials by default.
kiapi run --relay gcp
```

The requester writes
`{prefix}/sessions/{session_id}/request.json` in GCS, then writes a notification
to `{prefix}/nodes/{node_id}/requests/{session_id}` in RTDB. The relay reports
`queued`, `running`, and the terminal result below the requester node's
`responses` path.

- Requests are dispatched directly to the in-process FastAPI app and handled
  one at a time by the relay.
- JSON responses use `response.json`. Binary responses write `response.body`
  before `response.json`.
- `response.json` uses a GCS create-only generation precondition. A completed
  response found after restart is reported without executing the API again.
- The terminal RTDB response and request deletion use one atomic multi-location
  update.
- Startup installs a prefix-scoped lifecycle rule that deletes session objects
  after one day. Set `KIAPI_RELAY_GCP_MANAGE_BUCKET_LIFECYCLE=false` when
  infrastructure manages this rule.

Use a dedicated bucket and narrowly scoped RTDB/GCS permissions. Google
credentials are configured through
[`kiarina-lib-google`](https://github.com/kiarina/kiarina-python/tree/main/packages/kiarina-lib-google).

See [GCP Relay setup](../kiapi-relay/src/kiapi_relay/gcp/README.md) for resource
creation, IAM, authentication, configuration, and verification steps.

For local relay verification without GCP, use `local`. It uses the same
in-process dispatch path but stores notifications and payloads under a local
directory:

```sh
export KIAPI_RELAY_LOCAL_NODE_ID="studio-1"
export KIAPI_RELAY_LOCAL_ROOT="/tmp/kiapi/relay"
export KIAPI_RELAY_LOCAL_PREFIX="private/kiapi"

kiapi run --relay local
```

The requester writes `{root}/{prefix}/sessions/{session_id}/request.json`, then
writes `{root}/{prefix}/nodes/{node_id}/requests/{session_id}.json` with
`{"session_id":"...","source_node_id":"..."}`. The relay writes bridge status
to `{root}/{prefix}/nodes/{source_node_id}/responses/{session_id}.json` and
stores the committed response in the session directory.

## Local Storage

kiapi mainly writes to these local paths at runtime.

| Purpose | Setting | Default | Notes |
|---|---|---|---|
| Files API uploads, generated artifacts, and URL/data URL inputs | `KIAPI_FILES_ROOT` | `/tmp/kiapi/files` | Storage referenced by `file_id`. The default may disappear after OS reboot or tmp cleanup. Use `~/.kiapi/files` or external storage for long-term retention. |
| Temporary working directories during request processing | `KIAPI_TMP_ROOT` | `/tmp/kiapi/work` | Used for chat/embedding input expansion, generation intermediates, LoRA training work, and similar tasks. |
| Web backend subprocess logs | `KIAPI_WEB_BACKEND_LOG_DIR` | `/tmp/kiapi/logs/web` | stdout/stderr for SearXNG / Crawl4AI Docker subprocesses. |
| ACE-Step dedicated venv / project / checkpoints | `KIAPI_ACESTEP_PYTHON_PATH`, `KIAPI_ACESTEP_PROJECT_ROOT`, `KIAPI_ACESTEP_CHECKPOINT_DIR` | `KIAPI_USER_DATA_DIR` or `acestep/` under the platformdirs user data dir | When `python_path`, `project_root`, and `checkpoint_dir` are omitted, kiapi places the ACE-Step venv and checkpoints under a persistent ACE-Step directory. |

Other model weights and library caches are managed by Hugging Face, mflux,
Docker, or each library/tool. kiapi generally does not move them into its own
storage location.

## Security

By default, `kiapi run` starts on `127.0.0.1:8000`.
When `--host 0.0.0.0` is specified, the server may be reachable from other
machines, so use it only on trusted networks.
