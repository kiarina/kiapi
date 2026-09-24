# Changelog

All notable changes to the kiapi project will be documented in this file.

Entries before the single-package restructure prefix package-specific notes with
the package name (e.g. `**kiapi**:`).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed

- chat: removed the `qwen3.6-27b` model (alias `qwen3.6`). `qwen3.8-27b` uses the
  same handler, modalities and memory footprint; `vlm` selects `qwen3.8-flash-next`.
  Remove the downloaded weights with `kiapi deactivate --repo mlx-community/Qwen3.6-27B-4bit`.

### Changed

- chat: **`model` is now required** on `/v1/chat/completions`; there is no default
  chat model. Requests without it return HTTP 422. The chat models differ in
  accepted input modalities (only `qwen3-omni` takes audio/video) and memory
  footprint (`qwen3.8-flash-next` keeps about 74 GiB resident), so an implicit
  default could silently evict other models or reject media.
- chat: the aliases `vlm` and `qwen3.8` now select `qwen3.8-flash-next`
  (previously `qwen3.8-27b`). `qwen3.8-flash-next` also answers to
  `qwen3.8-flash` and `flash-next`; its `qwen4_exp` alias was removed.
  `qwen3.8-27b` keeps `qwen3_5` and `qwen3-vl`.

### Added

- chat: Qwen3.8-Flash-Next reuses unchanged history when images are appended,
  like Qwen3.8-27B, through the pinned mlx-vlm fork (`6581ba8c`).

- chat: added the `qwen3.8-flash-next` model (`mlx-community/Qwen3.8-Flash-Next-4bit`,
  aliases `qwen3.8-flash`, `flash-next`, `qwen4_exp`). It loads through a view that
  memory-maps its n-gram (PLE) table, which keeps about 80 GB resident instead of
  111.5 GB, and raises the open-file limit the mapped table needs.

- chat: Omni reuses unchanged prefixes when images, audio clips or videos are
  appended, including demuxed audiovisual inputs, through a pinned mlx-vlm fork.
- chat: the pinned engine supports multiple audio clips with independent feature
  extraction/encoding and corrected CNN lengths and chunk masks.

- chat: Qwen3.8 reuses unchanged image history when new images are appended,
  using a pinned mlx-vlm fork in uv-managed checkouts. Official-engine installs
  retain the conservative whole-request fallback.

- chat: client disconnects now cancel queued work or stop running generation at
  the next token boundary. Cancellation uses the existing `canceled` job state
  and safely clears APC state when a generator closes early.
- chat: responses report APC reuse through the OpenAI-compatible
  `usage.prompt_tokens_details.cached_tokens` field. Streaming requests support
  `stream_options.include_usage` and emit usage before `[DONE]` when requested.
- chat: bounded, memory-only automatic prefix caching for Qwen3.6 / Qwen3.8
  text and images, and Qwen3-Omni text, image, audio, video, and image + video.
  Media content hashes and video options protect cache identity, and Omni
  restores complete-prompt positions when reusing media prefixes.
- chat: `GET /v1/models` returns each model's `context_window`, read from the
  model's `config.json` (`null` until the model is set up).

### Changed

- **BREAKING**: chat: removed the `max_tokens_cap` setting
  (`KIAPI_CHAT_MAX_TOKENS_CAP`, 4096). `max_completion_tokens` is no longer
  capped by the server; generation stops at `max_completion_tokens` or when the
  prompt plus the output fills the model's context window, whichever comes first.
- chat: the default `max_completion_tokens` is now 1024 (was 512).
- chat: non-streaming requests now run through `stream_generate` like streaming
  ones, so the context window bound applies to both.

### Fixed

- chat: suppress extra streamed tool names when `parallel_tool_calls=false`.

- memory: include idle chat caches in cross-model eviction and transient reservations,
  and derive active cache headroom from the configured APC capacity.

- chat: `finish_reason` is now `"length"` when generation stops at
  `max_completion_tokens` or the context window. It was always `"stop"`.

## [0.7.0] - 2026-09-16

### Added

- ltx2: added the `ltx-2.5-distilled` model (`Lightricks/LTX-2.5`) and made it
  the default. `distilled` (LTX-2) remains available. LTX-2.5 adds the request
  options `auto_duration`, `enhance_prompt`, `pipeline="dfr"`, and
  `video_decoder="diffusion"`. Run `kiapi activate --family ltx2` to install the
  new mlx-video and the gated LTX-2.5 weights (about 83 GB including the prompt
  enhancer and DFR adapter).
- setup: `HfSnapshotResource` accepts `allow_patterns` so a model can download
  only the files it loads from a large repo.
- chat: added the `qwen3.8-27b` model (`mlx-community/Qwen3.8-27B-4bit`, aliases
  `qwen3.8`, `qwen3_5`, `qwen3-vl`, `vlm`). The last three moved from
  `qwen3.6-27b`, which keeps only `qwen3.6`. It runs on the existing `qwen3_5`
  handler (text + image, Hermes/XML tool calls, reasoning off by default).

### Fixed

- chat: image and video input failed on every model with
  `TypeError: repeat(): incompatible function arguments` since mlx 0.32. Fixed by
  updating mlx-vlm (below).
- chat: Qwen3-Omni now receives its deepstack visual features. mlx-vlm 0.6.3
  computed them but dropped them before the decoder, so image/video input used
  less of the vision tower than intended.
- chat: Qwen3-Omni video input no longer decodes garbage or crashes the server
  with a Metal GPU address fault on mlx-vlm 0.7.1. The deepstack mask and
  features are now windowed to each prefill chunk (patch H, upstream #2099).
- chat: Qwen3-Omni placed the video deepstack rows at the wrong positions when a
  prompt had both an image and a video. Patch C now rewrites that join as in
  upstream PR #2257 instead of grafting `mx.where` / `mx.scatter` onto mlx.

### Changed

- chat: updated `mlx-vlm` from 0.6.3 to 0.7.1 (still pinned exactly). The
  streaming UTF-8 and `mx.repeat` patches are removed because upstream fixed
  both; the stereo-audio, `mx.where`/`mx.scatter`, and stream-text patches stay.
  `mlx-lm` is now declared directly because mlx-embeddings' Qwen3-VL model
  imports it and mlx-vlm no longer pulls it in.
- Restructured the repository from a uv workspace (`packages/kiapi`) into a
  single package: the source now lives in `src/kiapi/`, the tests in `tests/`,
  and the release workflow builds and publishes `kiapi` directly. The package
  README and CHANGELOG are merged into the root ones, and the root `VERSION`
  file is replaced by the `version` in `pyproject.toml`.
- Updated dependencies. FastAPI moves to `>=0.141` (`build_openapi` now walks `routing.iter_route_contexts` to handle the lazy included routers of FastAPI 0.137+; the generated OpenAPI documents are unchanged), and the `numpy<2.5` cap is lifted (numba >= 0.67 supports numpy 2.5; the out-of-band LTX-2 install needs `numba>=0.67`).
- Refreshed the locked dependencies: torch 2.14, torchvision 0.29,
  huggingface-hub 1.30, tokenizers 0.23.2, anyio 4.15, and ruff 0.16.6.
- Updated the GitHub Actions used by CI, the PyPI release, and the Pages deploy
  to their current majors. `upload-pages-artifact` now sets
  `include-hidden-files: true` so `public/.nojekyll` keeps being published.
- Raised the mise pinned in CI and the release workflow from 2026.5.0 to 2026.9.1,
  the version `mise run ci` is verified against locally.
- Replaced the Dependabot configuration: the npm ecosystem entry pointed at the
  `package.json` removed in 0.6.0, so it is dropped in favour of the `uv` and
  `github-actions` ecosystems. `mlx-vlm` is ignored there for the same reason it
  is pinned.

### Removed

- Removed the Node tooling (`package.json` / pnpm / `firebase-tools`) that existed only for the retired GCP relay setup task. This clears all open Dependabot alerts, which were transitive dependencies of `firebase-tools`.

## [0.6.0] - 2026-09-01

### Removed

- **BREAKING**: Removed the relay transport and retired the `kiapi-relay` and `kiapi-proxy` packages. `kiapi run --relay`, the `relay-gcp` extra, the `relay` field of `/health`, and the `KIAPI_RELAY_*` settings are gone. To reach kiapi from other machines, expose it over your own private network layer instead — for example, run `tailscale serve --bg --https=8500 8500` on the kiapi machine and point clients at `https://<machine>.<tailnet>.ts.net:8500`. The published `kiapi-relay` / `kiapi-proxy` distributions remain on PyPI as-is but will receive no further updates. (The unreleased GCP RTDB watch read-timeout fix was removed together with the relay.)

## [0.5.3] - 2026-07-30

### Fixed

- **kiapi**: `kiapi service install` now preserves `PATH` in the launchd property list so background capabilities can find external tools such as Homebrew FFmpeg.

## [0.5.2] - 2026-07-29

### Fixed

- Publish each workspace package with its own PyPI Trusted Publishing token so a release can upload multiple projects.

## [0.5.1] - 2026-07-29

### Added

- **kiapi**: `kiapi run --relay none` explicitly disables the relay, overriding a relay enabled in user settings.
- **kiapi-relay**: `KIAPI_RELAY_DEFAULT=none` (and other `KIAPI_RELAY_*` env vars set to `none`) is now parsed as unset, so the relay can be disabled via the environment.

### Fixed

- **kiapi-relay**: Reconnect the GCP RTDB request stream when Firebase reports an expired credential or canceled subscription, instead of leaving the relay unable to receive new requests.

## [0.5.0] - 2026-07-11

### Fixed

- **kiapi** / **kiapi-proxy**: `service install` now also pins `XDG_CACHE_HOME` in the launchd property list so the background service uses the same cache directory and single-instance lock as the interactive CLI.

## [0.4.0] - 2026-07-11

### Added

- **kiapi**: Added `kiapi service show` to print the installed launchd property list.

### Changed

- **kiapi-relay**: The `gcp:setup` task no longer passes `--scopes` to
  `gcloud auth application-default login`. The default ADC scopes already
  include `cloud-platform`, which covers the GCS and RTDB access the relay
  needs, so the extra scopes were unnecessary.
- **kiapi-relay**: The `gcp:setup` Impersonation method now runs
  `gcloud auth application-default login` itself instead of only reminding the
  user to, since ADC is the base credential the impersonation chain mints SA
  tokens from, and grants `roles/iam.serviceAccountTokenCreator` to the actual
  ADC principal rather than the active gcloud CLI account.

### Fixed

- **kiapi**: `kiapi service install` now pins the current `XDG_CONFIG_HOME` and `XDG_DATA_HOME` values in the launchd property list so the background service resolves the same user settings and data directories as the interactive CLI.
- **kiapi**: The hot-reload worker subprocess (`kiapi run --debug`) now loads the user settings file in the ASGI factory, so relays configured only in user settings (for example the GCP relay's `database_url`/`bucket`) start correctly. Previously `kiapi run --relay gcp --debug` failed at startup with "required field is not set" because the reload subprocess never ran `load_user_settings()`.

## [0.3.0] - 2026-07-02

### Added

- Manage Node dev tooling with pnpm through a root `package.json`; `firebase-tools` is now a project-local dev dependency installed by `mise run setup` (`pnpm install`) rather than a global `npm install -g`, and mise puts it on `PATH` via `node_modules/.bin`.
- **kiapi-relay**: Added a `gcp:setup` mise task (run from `packages/kiapi-relay/`) that interactively provisions the GCS bucket, Firebase Realtime Database instance, and authentication for `GCPRelay`, then prints the kiapi YAML to paste with `kiapi config edit`. It uses the project-local `firebase-tools`. The task verifies `firebase-tools` has its own login (via `firebase login:list`) instead of relying on `firebase projects:list`, which also succeeds through the Application Default Credentials fallback and then fails the Realtime Database calls with a quota-project 403; the RTDB creation failure message now points at `firebase-debug.log` and lists both the missing-login and Blaze-plan causes. The GCP relay README was rewritten around this task.
- **kiapi**: `GET /health` now reports the status of the relay started with the server in a `relay` field (`name`, `running`, `failed`), or `null` when no relay is configured.
- **kiapi-relay**: Added a `name` attribute to the `Relay` protocol, populated by the relay registry through a `factory_wrapper` and shared via a new `BaseRelay` base class. `RelayRunner.status()` returns a new `RelayHealth` view (`name`, `running`, `failed`).
- **kiapi**: Added a `request` method to the `Relay` protocol and implemented it on `LocalRelay` and `GCPRelay`, promoting the relay request client from the verification scripts into the relay packages. Responses are returned as `RelayResponse`, with binary bodies materialized to a temporary file the caller owns.
- **kiapi-relay**: Relay participants derive a stable `node_id` from a data directory (`get_or_create_node_id`), and discover a target node through liveness heartbeats published under `liveness/{node_id}` as part of the `watch` lifecycle (`heartbeat_interval_s`/`liveness_ttl_s` settings); `Relay.request` fails with `no_relay_node` when none is fresh.
- **kiapi-proxy**: Expanded the CLI to mirror the `kiapi` command layout so the proxy is managed independently: `config` (`init`/`show`/`edit`/`template`) manages a user settings file separate from kiapi's (holding `kiapi_proxy.api` and `kiapi_relay` settings, loaded on every command); `check --relay local|gcp` sends a single request (default `/health`, overridable with `--path`) through the relay to a live kiapi node and prints the response without starting the server, so relay connectivity can be verified as a health check (it reuses the persistent relay `node_id` and holds the single-instance lock like `run`, failing fast if the proxy server is already running); `service` (`install`/`start`/`status`/`stop`/`uninstall`) manages a launchd user agent (`io.github.kiarina.kiapi-proxy`) that runs `kiapi-proxy run` (`install` pins the `XDG_CONFIG_HOME`/`XDG_DATA_HOME` values present at install time into the plist, since launchd does not inherit them, so the service resolves the same config/data directories as the interactive shell and can find the user settings written by `config edit`).
- **kiapi** / **kiapi-proxy**: Each server resolves a persistent relay `node_id` from its user data directory, injects it into the relay, and acquires a single-instance lock (via `kiarina-utils-app`, scoped to the user cache directory) so a second process cannot share the same node identity.
- **kiapi-relay**: Initial release of `kiapi-relay`, extracted from `kiapi`. Provides the relay protocol, request/response schemas, the in-process `RelayRunner`, and the relay request client, plus the local filesystem (`kiapi_relay.impl.local`) and GCP (`kiapi_relay.impl.gcp`, available via the `gcp` extra) relay backends.
- **kiapi-proxy**: Initial release of `kiapi-proxy`: a proxy server that forwards incoming HTTP requests to a kiapi instance over a relay (`kiapi-relay`) and returns the result. Supports JSON responses, file/binary responses, and chat `text/event-stream` responses re-emitted as Server-Sent Events. Ships a `kiapi-proxy` CLI and does not depend on `kiapi` or MLX, so it runs on Linux, Windows, and resource-constrained machines.

### Changed

- Reworked `mise run verify` into a Python driver (`scripts/verify.py`) that selects a target (`--kiapi` / `--kiapi-relay` / `--kiapi-proxy`, or fzf-interactive), starts and stops the kiapi / kiapi-proxy servers it needs (stopping and restarting the launchd services if they are running), and runs the matching verification scripts. It replaces the old per-capability and `relay*` task arguments; scope with `--family` and `--relay` instead, or run an individual `scripts/capabilities/verify_*.py` directly. Capability verify output now honours `KIAPI_VERIFY_DIR` (default `.verify`), and the driver routes artifacts to `.verify/kiapi` vs `.verify/kiapi-proxy` so direct and proxied runs no longer collide. The relay verify scripts were consolidated into `scripts/relay/verify_local.py` and `scripts/relay/verify_gcp.py` (which gain the core files/jobs CRUD checks); the capability-heavy `scripts/relay/verify.py` was removed, since capabilities are now covered through the proxy path. The `Makefile` verify targets are now `verify` / `verify-fast` / `verify-kiapi` / `verify-kiapi-relay` / `verify-kiapi-proxy`.
- Moved development and CI operations from Make recipes into package-aware mise tasks, including the new setup task and namespaced test-assets download task.
- Manage the repository version in a single root `VERSION` file and release the whole workspace under one shared version. The release pipeline now detects packages with unreleased changelog entries, bumps and publishes only those, and is triggered by a single `v<version>` tag instead of per-package `<package>-v<version>` tags.
- **kiapi-relay**: The relay `node_id` is now generated automatically and persisted per data directory instead of being configured. The manual `node_id`/`source_node_id` settings were removed from the local and GCP backends; clients discover a target node through liveness heartbeats and address responses with their own generated `node_id`.
- **kiapi**: Simplified the `Relay` protocol to a single `watch` method and moved listener tasks and the HTTP client into the `watch` lifecycle, removing the explicit `close` method.
- **kiapi**: Reworked the relay verification scripts to issue requests through `Relay.request` via the relay registry factories, removing the duplicated transport client in `scripts/relay/_client.py`.
- **kiapi**: Converted the repository into a uv workspace and moved the `kiapi` package to `packages/kiapi/` with a `src/` layout. Packaging and lint/test paths are now per-package.
- **kiapi**: Extracted the relay subsystem into a separate `kiapi-relay` package. `kiapi.core.relay` is now `kiapi_relay`, and `kiapi.relay.{local,gcp}` are now `kiapi_relay.{local,gcp}`. The `relay-gcp` extra now pulls `kiapi-relay[gcp]`.
- **kiapi** / **kiapi-proxy**: User-directory resolution and single-instance locking are delegated to the shared `kiarina-utils-app` package and used directly (`kiarina.utils.app`) rather than through a `core.app` re-export layer, removing the private `AppSettings`/user-directory copy and the direct `platformdirs` dependency. kiapi's `core.app` now provides only the `AppContext` schema; kiapi-proxy's `core.app` module was removed. Each server sets the app identity by calling `kiarina.utils.app.configure(...)` at its CLI entry point (and, for kiapi, the ASGI factory used by hot reload). The directory getters return `pathlib.Path`. For kiapi, the user `settings.yaml` section for these settings moves from `kiapi.core.app` to `kiarina.utils.app`; the override environment variables are `KIARINA_UTILS_APP_`.
