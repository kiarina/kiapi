# Changelog

All notable changes to the kiapi project will be documented in this file.

This file contains the overall project changes. For package-specific changes,
see the `CHANGELOG.md` in each package directory under `packages/`.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Manage Node dev tooling with pnpm through a root `package.json`; `firebase-tools` is now a project-local dev dependency installed by `mise run setup` (`pnpm install`) rather than a global `npm install -g`, and mise puts it on `PATH` via `node_modules/.bin`.
- **kiapi-relay**: Added a `gcp:setup` mise task (run from `packages/kiapi-relay/`) that interactively provisions the GCS bucket, Firebase Realtime Database instance, and authentication for `GCPRelay`, then prints the kiapi YAML to paste with `kiapi config edit`. It uses the project-local `firebase-tools`. The task verifies `firebase-tools` has its own login (via `firebase login:list`) instead of relying on `firebase projects:list`, which also succeeds through the Application Default Credentials fallback and then fails the Realtime Database calls with a quota-project 403; the RTDB creation failure message now points at `firebase-debug.log` and lists both the missing-login and Blaze-plan causes. The GCP relay README was rewritten around this task.
- **kiapi**: `GET /health` now reports the status of the relay started with the server in a `relay` field (`name`, `running`, `failed`), or `null` when no relay is configured.
- **kiapi-relay**: Added a `name` attribute to the `Relay` protocol, populated by the relay registry through a `factory_wrapper` and shared via a new `BaseRelay` base class. `RelayRunner.status()` returns a new `RelayHealth` view (`name`, `running`, `failed`).
- **kiapi**: Added a `request` method to the `Relay` protocol and implemented it on `LocalRelay` and `GCPRelay`, promoting the relay request client from the verification scripts into the relay packages. Responses are returned as `RelayResponse`, with binary bodies materialized to a temporary file the caller owns.
- **kiapi-relay**: Relay participants derive a stable `node_id` from a data directory (`get_or_create_node_id`), and discover a target node through liveness heartbeats published under `liveness/{node_id}` as part of the `watch` lifecycle (`heartbeat_interval_s`/`liveness_ttl_s` settings); `Relay.request` fails with `no_relay_node` when none is fresh.
- **kiapi-proxy**: Expanded the CLI to mirror the `kiapi` command layout so the proxy is managed independently: `config` (`init`/`show`/`edit`/`template`) manages a user settings file separate from kiapi's (holding `kiapi_proxy.api` and `kiapi_relay` settings, loaded on every command); `check --relay local|gcp` sends a single request (default `/health`, overridable with `--path`) through the relay to a live kiapi node and prints the response without starting the server, so relay connectivity can be verified as a health check (it reuses the persistent relay `node_id` and holds the single-instance lock like `run`, failing fast if the proxy server is already running); `service` (`install`/`start`/`status`/`stop`/`uninstall`) manages a launchd user agent (`io.github.kiarina.kiapi-proxy`) that runs `kiapi-proxy run`.
- **kiapi** / **kiapi-proxy**: Each server resolves a persistent relay `node_id` from its user data directory, injects it into the relay, and acquires a single-instance lock (via `kiarina-utils-app`, scoped to the user cache directory) so a second process cannot share the same node identity.
- **kiapi-relay**: Initial release of `kiapi-relay`, extracted from `kiapi`. Provides the relay protocol, request/response schemas, the in-process `RelayRunner`, and the relay request client, plus the local filesystem (`kiapi_relay.impl.local`) and GCP (`kiapi_relay.impl.gcp`, available via the `gcp` extra) relay backends.
- **kiapi-proxy**: Initial release of `kiapi-proxy`: a proxy server that forwards incoming HTTP requests to a kiapi instance over a relay (`kiapi-relay`) and returns the result. Supports JSON responses, file/binary responses, and chat `text/event-stream` responses re-emitted as Server-Sent Events. Ships a `kiapi-proxy` CLI and does not depend on `kiapi` or MLX, so it runs on Linux, Windows, and resource-constrained machines.

### Changed

- Moved development and CI operations from Make recipes into package-aware mise tasks, including the new setup task and namespaced test-assets download task.
- Manage the repository version in a single root `VERSION` file and release the whole workspace under one shared version. The release pipeline now detects packages with unreleased changelog entries, bumps and publishes only those, and is triggered by a single `v<version>` tag instead of per-package `<package>-v<version>` tags.
- **kiapi-relay**: The relay `node_id` is now generated automatically and persisted per data directory instead of being configured. The manual `node_id`/`source_node_id` settings were removed from the local and GCP backends; clients discover a target node through liveness heartbeats and address responses with their own generated `node_id`.
- **kiapi**: Simplified the `Relay` protocol to a single `watch` method and moved listener tasks and the HTTP client into the `watch` lifecycle, removing the explicit `close` method.
- **kiapi**: Reworked the relay verification scripts to issue requests through `Relay.request` via the relay registry factories, removing the duplicated transport client in `scripts/relay/_client.py`.
- **kiapi**: Converted the repository into a uv workspace and moved the `kiapi` package to `packages/kiapi/` with a `src/` layout. Packaging and lint/test paths are now per-package.
- **kiapi**: Extracted the relay subsystem into a separate `kiapi-relay` package. `kiapi.core.relay` is now `kiapi_relay`, and `kiapi.relay.{local,gcp}` are now `kiapi_relay.{local,gcp}`. The `relay-gcp` extra now pulls `kiapi-relay[gcp]`.
- **kiapi** / **kiapi-proxy**: User-directory resolution and single-instance locking are delegated to the shared `kiarina-utils-app` package and used directly (`kiarina.utils.app`) rather than through a `core.app` re-export layer, removing the private `AppSettings`/user-directory copy and the direct `platformdirs` dependency. kiapi's `core.app` now provides only the `AppContext` schema; kiapi-proxy's `core.app` module was removed. Each server sets the app identity by calling `kiarina.utils.app.configure(...)` at its CLI entry point (and, for kiapi, the ASGI factory used by hot reload). The directory getters return `pathlib.Path`. For kiapi, the user `settings.yaml` section for these settings moves from `kiapi.core.app` to `kiarina.utils.app`; the override environment variables are `KIARINA_UTILS_APP_`.
