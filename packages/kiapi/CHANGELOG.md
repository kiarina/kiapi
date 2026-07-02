# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Fixed

- The hot-reload worker subprocess (`kiapi run --debug`) now loads the user settings file in the ASGI factory, so relays configured only in user settings (for example the GCP relay's `database_url`/`bucket`) start correctly. Previously `kiapi run --relay gcp --debug` failed at startup with "required field is not set" because the reload subprocess never ran `load_user_settings()`.

## [0.3.0] - 2026-07-02

### Added

- `GET /health` now reports the status of the relay started with the server in a `relay` field (`name`, `running`, `failed`), or `null` when no relay is configured.
- Added a `request` method to the `Relay` protocol and implemented it on `LocalRelay` and `GCPRelay`, promoting the relay request client from the verification scripts into the relay packages. Responses are returned as `RelayResponse`, with binary bodies materialized to a temporary file the caller owns.
- The server now resolves a persistent relay `node_id` from its user data directory and injects it into the relay, and acquires a single-instance lock (via `kiarina-utils-app`, scoped to the user cache directory) at startup so a second `kiapi` cannot share the same node identity. Added a `request_poll_interval_s` setting for GCP request polling.

### Changed

- The relay `node_id` is now generated automatically and persisted per data directory instead of being configured. The manual `node_id`/`source_node_id` relay settings were removed; clients discover a target node through liveness heartbeats and address responses with their own generated `node_id`.
- Simplified the `Relay` protocol to a single `watch` method and moved listener tasks and the HTTP client into the `watch` lifecycle, removing the explicit `close` method.
- Reworked the relay verification scripts to issue requests through `Relay.request` via the relay registry factories, removing the duplicated transport client in `scripts/relay/_client.py`.
- Converted the repository into a uv workspace and moved the `kiapi` package to `packages/kiapi/` with a `src/` layout. Packaging and lint/test paths are now per-package.
- Extracted the relay subsystem into a separate `kiapi-relay` package. `kiapi.core.relay` is now `kiapi_relay`, and `kiapi.relay.{local,gcp}` are now `kiapi_relay.{local,gcp}`. The `relay-gcp` extra now pulls `kiapi-relay[gcp]`.
- User-directory resolution and single-instance locking are delegated to the shared `kiarina-utils-app` package and used directly (`kiarina.utils.app`) rather than through a `core.app` re-export layer, removing the private `AppSettings`/user-directory copy and the direct `platformdirs` dependency. `kiapi.core.app` now provides only the `AppContext` schema. The app identity is set by calling `kiarina.utils.app.configure("kiapi", "kiarina")` at the CLI entry (`kiapi ...`) and the ASGI factory used by hot reload. The directory getters return `pathlib.Path`. The user `settings.yaml` section for these settings moves from `kiapi.core.app` to `kiarina.utils.app`, and the override environment variables move from `KIAPI_` to `KIARINA_UTILS_APP_`.

## [0.2.0] - 2026-06-26

### Added

- Added an optional plugin-based remote job relay with Firebase Realtime Database notifications, GCS request/response payloads, in-process ASGI dispatch, committed-response recovery, and atomic terminal delivery.
- Added a filesystem-backed LocalRelay for local relay verification without GCP services.
- Added relay verification scripts for LocalRelay, GCPRelay, and end-to-end LocalRelay capability checks.

### Changed

- Moved GCP relay dependencies into the optional `relay-gcp` extra.
- Updated the minimum `pydantic-settings-manager` dependency to 3.7.0.

### Fixed

- Added the OAuth scopes required by the Firebase Realtime Database REST API to GCP relay credentials.
- Added relay support for multipart file uploads such as `POST /v1/files`.

## [0.1.0] - 2026-06-23

### Added

- Initial release.
- Added release automation with mise tasks for version bumps, changelog updates, changelog extraction, package builds, and PyPI publishing.
- Added a tag-driven GitHub Actions release workflow that builds distributions, creates GitHub Releases from `CHANGELOG.md`, and publishes to PyPI.
- Added pull request and main-branch CI for tests, formatting/linting, documentation generation, and package builds.
- Added contribution and security policy documentation for public OSS use.
- Added PyPI classifiers and keywords to improve package metadata.
- Made PyPI publishing failures fail the release workflow instead of being ignored.

### Changed

- Updated GitHub Actions CI and release jobs from `macos-14` to `macos-15`.

### Fixed

- Declared `uv` in `mise.toml` so GitHub Actions installs it before running `uv sync`.
- Moved PyPI publishing to a Linux runner while keeping macOS release checks and builds.
