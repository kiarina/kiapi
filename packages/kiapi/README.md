# kiapi

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Apple%20Silicon-lightgrey.svg)
[![API Docs](https://img.shields.io/badge/API%20Docs-GitHub%20Pages-green.svg)](https://kiarina.github.io/kiapi/)

**English** | [日本語](README.ja.md)

## Summary

kiapi is an **API server** for providing the following capabilities to
**LLM agents** on a **Mac Studio M4 Max 128GB**.

- **Chat:**
  - OpenAI Chat Completions API compatible
  - text + image + audio + video input support
  - tool call + tool choice (auto, any, specific) + parallel tool calls + streaming support
- **Embedding:**
  - text + image input support
- **Image generation:**
  - text2image, image2image, image editing, and LoRA training support
- **Music and sound-effect generation:**
  - text2audio, cover, repaint, and extract support
- **Video generation:**
  - text2video, image2video, and audio2video support
- **Web:**
  - search + fetch support

To provide every capability stably from a single PC, kiapi has these properties.

- GPU work is queued and executed **one job at a time**
- Application **memory is managed** to avoid overcommit failures

kiapi is also designed so LLM agents can understand and operate its capabilities.

- The API server can **explain how to use itself** to an LLM
- Asynchronous task **progress can be observed**
- Generation tasks can run in both **sync / async** modes

> [!IMPORTANT]
>
> kiapi itself is MIT-licensed OSS, but the packages and models it provides have
> various licenses. Before use, check the dependency packages and models on each
> capability page and confirm the license of the model you use.

## Model and Dependency Licenses

The table below summarizes the upstream licenses for the default models and
runtime resources that kiapi can activate. It is a convenience checklist, not
legal advice. License labels and gating status can change upstream, so always
check the linked source before commercial use, redistribution, or offering a
hosted service.

Review date: 2026-06-23.

| Domain | Family | Resource | Kind | Upstream license | Notes |
|---|---|---|---|---|---|
| chat | chat | [mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit) | model weights | Apache-2.0 | MLX-converted Qwen3 Omni model. |
| chat | chat | [mlx-community/Qwen3.6-27B-4bit](https://huggingface.co/mlx-community/Qwen3.6-27B-4bit) | model weights | Apache-2.0 | MLX-converted Qwen3.6 model. |
| embedding | embedding | [mlx-community/Qwen3-Embedding-8B-mxfp8](https://huggingface.co/mlx-community/Qwen3-Embedding-8B-mxfp8) | model weights | Apache-2.0 | Text embedding model. |
| embedding | embedding | [mlx-community/Qwen3-VL-Embedding-2B-mxfp8](https://huggingface.co/mlx-community/Qwen3-VL-Embedding-2B-mxfp8) | model weights | Apache-2.0 | Text + image embedding model. |
| image | zimage | [filipstrand/Z-Image-Turbo-mflux-4bit](https://huggingface.co/filipstrand/Z-Image-Turbo-mflux-4bit) | model weights | Tongyi Qianwen License | Quantized MLX-compatible Z-Image Turbo; inherits the original Z-Image Turbo license. |
| image | zimage | [Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image) | model weights | Apache-2.0 | Base Z-Image model. |
| image | flux2 | [black-forest-labs/FLUX.2-klein-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) | model weights | FLUX Non-Commercial License | Gated upstream model. Confirm terms before any commercial use. |
| image | flux2 | [black-forest-labs/FLUX.2-klein-base-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B) | model weights | Apache-2.0 | Open-weight FLUX.2 Klein Base 4B variant. |
| image | flux2 | [black-forest-labs/FLUX.2-klein-base-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) | model weights | FLUX Non-Commercial License | Gated upstream model. Confirm terms before any commercial use. |
| image | qwen | [Qwen/Qwen-Image](https://huggingface.co/Qwen/Qwen-Image) | model weights | Apache-2.0 | Text-to-image model. |
| image | qwen | [Qwen/Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509) | model weights | Apache-2.0 | Image editing model. |
| image | ideogram4 | [ideogram-ai/ideogram-4-fp8](https://huggingface.co/ideogram-ai/ideogram-4-fp8) | model weights | Ideogram Non-Commercial Model Agreement | Gated upstream model. Confirm hosted-service and commercial-use terms. |
| image | ernie | [baidu/ERNIE-Image-Turbo](https://huggingface.co/baidu/ERNIE-Image-Turbo) | model weights | Apache-2.0 | Turbo ERNIE-Image variant. |
| image | ernie | [baidu/ERNIE-Image](https://huggingface.co/baidu/ERNIE-Image) | model weights | Apache-2.0 | Base ERNIE-Image variant. |
| image | seedvr2 | [numz/SeedVR2_comfyUI](https://huggingface.co/numz/SeedVR2_comfyUI) | model weights | Apache-2.0 | SeedVR2 3B and 7B upscaling checkpoints. |
| image | depthpro | [apple/ml-depth-pro](https://github.com/apple/ml-depth-pro) / [depth_pro.pt](https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt) | code + model file | Apple custom license | GitHub reports `NOASSERTION`; review Apple's license text before redistribution or commercial use. |
| audio | acestep | [ace-step/ACE-Step-1.5](https://github.com/ace-step/ACE-Step-1.5) | Python package | MIT | Installed into the ACE-Step dedicated venv. |
| audio | acestep | [ACE-Step/Ace-Step1.5](https://huggingface.co/ACE-Step/Ace-Step1.5) | shared checkpoints | MIT | Shared ACE-Step 1.5 checkpoint resources. |
| audio | acestep | [ACE-Step/acestep-v15-xl-base](https://huggingface.co/ACE-Step/acestep-v15-xl-base) | model weights | MIT | Extra XL base checkpoint used by `xl-base`. |
| audio | audiogen | [facebook/audiogen-medium](https://huggingface.co/facebook/audiogen-medium) | model weights | CC-BY-NC-4.0 | Non-commercial license. |
| video | ltx2 | [Blaizzy/mlx-video](https://github.com/Blaizzy/mlx-video) | Python package | MIT | Installed from a pinned Git commit for LTX-2 inference. |
| video | ltx2 | [prince-canuma/LTX-2-distilled](https://huggingface.co/prince-canuma/LTX-2-distilled) | model weights | Not declared upstream | The model card has no license metadata; verify rights before use. |
| web | web | [searxng/searxng](https://github.com/searxng/searxng) / `searxng/searxng:latest` | Docker image | AGPL-3.0 | Web search backend. AGPL obligations can matter for network services. |
| web | web | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) / `unclecode/crawl4ai:latest` | Docker image | Apache-2.0 | Web fetch backend. |

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

## API Docs

- [kiapi API Docs](https://kiarina.github.io/kiapi/)
  - [OpenAPI JSON](https://kiarina.github.io/kiapi/openapi.json)
  - [Swagger UI](https://kiarina.github.io/kiapi/docs.html)
  - [ReDoc](https://kiarina.github.io/kiapi/redoc.html)

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

## Quick Start

**From installation to agent integration:**

```sh
# Install kiapi itself
python3.12 -m pip install --upgrade kiapi  # when uv is unavailable
uv tool install --python 3.12 kiapi  # when uv is available

# Change default host, port, or memory budget if needed
kiapi config init
kiapi config edit

# Check setup status
kiapi status

# Explicit setup for model weights, Docker images, and dedicated venvs
kiapi activate  # select targets from the displayed list
kiapi activate --all  # set up everything (a little under 600GB)
kiapi activate --family acestep  # set up only one family

# Verify behavior
kiapi check  # select targets from the displayed list
kiapi check --all  # check everything

# Start the API server
kiapi run  # starts on 127.0.0.1:8000
kiapi run --host 0.0.0.0 --port 8500  # specify host and port

# Example agent integration
codex e "
Please understand http://localhost:8000/openapi.json.
Using the music generation API, generate a 20-second BGM themed 'a person walking in the rain' at ~/Downloads/bgm.wav.
"

# Check the generated file
open ~/Downloads/bgm.wav
```

**Run as a background service:**
```sh
# Register the service
kiapi service install

# Start the service
kiapi service start

# Check service status and log tail
kiapi service status

# Stop the service
kiapi service stop

# Remove the service
kiapi service uninstall
```

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

## Architecture

> [!NOTE]
>
> For kiapi architecture details, see
> [ARCHITECTURE.md](../../ARCHITECTURE.md).

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

## Project Status

kiapi is OSS developed mainly for personal use. The API, supported models, and
setup steps may change in the future.

Issues and Pull Requests are welcome, but this is a personal project and support
is best-effort.

## Security

By default, `kiapi run` starts on `127.0.0.1:8000`.
When `--host 0.0.0.0` is specified, the server may be reachable from other
machines, so use it only on trusted networks.

## Development

```sh
# Install dependencies, download test data, and create the venv environment
make init

# Sync dependencies
make update

# Upgrade dependencies
make upgrade

# ... implement

# Format, type-check, and regenerate documentation under public/
make

# unit test
make test

# Start the development server (auto-reload supported)
make dev

# GPU feature tests / regression tests
make verify  # run all
make verify-fast  # run only light tests for all capabilities
make verify-one  # run one capability
```

## Release

kiapi releases follow the same flow as `pydantic-settings-manager`: update the
version, update the changelog, then push a tag that triggers GitHub Release and
PyPI publishing.

```sh
# Update the version and release entry in CHANGELOG.md
make bump-version

# Or pass the version explicitly
mise run bump-version 0.2.0

# Local verification
make test
make
make build

# Release commit and tag
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): prepare v0.2.0"
git tag v0.2.0
git push origin main --tags
```

When a `v*.*.*` tag is pushed, the GitHub Actions release workflow builds the
package, extracts release notes from `CHANGELOG.md`, creates a GitHub Release,
and publishes to PyPI.
