# kiapi

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Apple%20Silicon-lightgrey.svg)
[![API Docs](https://img.shields.io/badge/API%20Docs-GitHub%20Pages-green.svg)](https://kiarina.github.io/kiapi/)

## Summary

kiapi is a local API server that uses Apple Silicon and MLX to provide generative AI capabilities for LLM agents.

## API

| Domain | Family | Endpoint | Description |
|---|---|---|---|
| chat |  | `POST /v1/chat` | [Chat API details](./src/kiapi/capabilities/chat/README.md) |
| embedding |  | `POST /v1/embedding` | [Embedding API details](./src/kiapi/capabilities/embedding/README.md) |
| image | zimage | `POST /v1/image/zimage` | [Z-Image API details](./src/kiapi/capabilities/zimage/README.md) |
|  | flux2 | `POST /v1/image/flux2` | [FLUX.2 API details](./src/kiapi/capabilities/flux2/README.md) |
|  | qwen | `POST /v1/image/qwen` | [Qwen Image API details](./src/kiapi/capabilities/qwen/README.md) |
|  | ideogram4 | `POST /v1/image/ideogram4` | [Ideogram 4 API details](./src/kiapi/capabilities/ideogram4/README.md) |
|  | ernie | `POST /v1/image/ernie` | [ERNIE-Image API details](./src/kiapi/capabilities/ernie/README.md) |
|  | seedvr2 | `POST /v1/image/seedvr2` | [SeedVR2 API details](./src/kiapi/capabilities/seedvr2/README.md) |
|  | depthpro | `POST /v1/image/depthpro` | [Depth Pro API details](./src/kiapi/capabilities/depthpro/README.md) |
| audio | acestep | `POST /v1/audio/acestep` | [ACE-Step API details](./src/kiapi/capabilities/acestep/README.md) |
|  | audiogen | `POST /v1/audio/audiogen` | [AudioGen API details](./src/kiapi/capabilities/audiogen/README.md) |
| video | ltx2 | `POST /v1/video/ltx2` | [LTX-2 API details](./src/kiapi/capabilities/ltx2/README.md) |
| web |  | `POST /v1/web` | [Web API details](./src/kiapi/capabilities/web/README.md) |
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

## Remote Access

kiapi binds to `127.0.0.1` by default and does not expose an inbound socket.
For access from other machines, put it behind your own private network layer —
for example `tailscale serve` for a TLS endpoint reachable only inside your
tailnet.

## Local Storage

kiapi mainly writes to these local paths at runtime.

| Purpose | Setting | Default | Notes |
|---|---|---|---|
| Files API uploads, generated artifacts, and URL/data URL inputs | `KIAPI_FILES_ROOT` | `/tmp/kiapi/files` | Storage referenced by `file_id`. The default may disappear after OS reboot or tmp cleanup. Use `~/.kiapi/files` or external storage for long-term retention. |
| Temporary working directories during request processing | `KIAPI_TMP_ROOT` | `/tmp/kiapi/work` | Used for chat/embedding input expansion, generation intermediates, LoRA training work, and similar tasks. |
| Web backend subprocess logs | `KIAPI_WEB_BACKEND_LOG_DIR` | `/tmp/kiapi/logs/web` | stdout/stderr for SearXNG / Crawl4AI Docker subprocesses. |
| ACE-Step dedicated venv / project / checkpoints | `KIAPI_ACESTEP_PYTHON_PATH`, `KIAPI_ACESTEP_PROJECT_ROOT`, `KIAPI_ACESTEP_CHECKPOINT_DIR` | `acestep/` under the user data dir | When `python_path`, `project_root`, and `checkpoint_dir` are omitted, kiapi places the ACE-Step venv and checkpoints under a persistent ACE-Step directory. |

Other model weights and library caches are managed by Hugging Face, mflux,
Docker, or each library/tool. kiapi generally does not move them into its own
storage location.

## Security

By default, `kiapi run` starts on `127.0.0.1:8000`.
When `--host 0.0.0.0` is specified, the server may be reachable from other
machines, so use it only on trusted networks.
