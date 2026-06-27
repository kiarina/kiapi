# Changelog

All notable changes to the kiapi project will be documented in this file.

This file contains the overall project changes. For package-specific changes,
see the `CHANGELOG.md` in each package directory under `packages/`.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **kiapi**: `GET /health` now reports the status of the relay started with the server in a `relay` field (`name`, `running`, `failed`), or `null` when no relay is configured.
- **kiapi-relay**: Added a `name` attribute to the `Relay` protocol, populated by the relay registry through a `factory_wrapper` and shared via a new `BaseRelay` base class. `RelayRunner.status()` returns a new `RelayHealth` view (`name`, `running`, `failed`).
- **kiapi**: Added a `request` method to the `Relay` protocol and implemented it on `LocalRelay` and `GCPRelay`, promoting the relay request client from the verification scripts into the relay packages. Responses are returned as `RelayResponse`, with binary bodies materialized to a temporary file the caller owns.
- **kiapi**: Added a `source_node_id` relay setting to identify the client when issuing relay requests, and a `request_poll_interval_s` setting for GCP request polling.
- **kiapi-relay**: Initial release of `kiapi-relay`, extracted from `kiapi`. Provides the relay protocol, request/response schemas, the in-process `RelayRunner`, and the relay request client, plus the local filesystem (`kiapi_relay.local`) and GCP (`kiapi_relay.gcp`, available via the `gcp` extra) relay backends.
- **kiapi-proxy**: Initial release of `kiapi-proxy`: a proxy server that forwards incoming HTTP requests to a kiapi instance over a relay (`kiapi-relay`) and returns the result. Supports JSON responses, file/binary responses, and chat `text/event-stream` responses re-emitted as Server-Sent Events. Ships a `kiapi-proxy` CLI and does not depend on `kiapi` or MLX, so it runs on Linux, Windows, and resource-constrained machines.

### Changed

- Moved development and CI operations from Make recipes into package-aware mise tasks, including the new setup task and namespaced test-assets download task.
- Manage the repository version in a single root `VERSION` file and release the whole workspace under one shared version. The release pipeline now detects packages with unreleased changelog entries, bumps and publishes only those, and is triggered by a single `v<version>` tag instead of per-package `<package>-v<version>` tags.
- **kiapi**: Simplified the `Relay` protocol to a single `watch` method and moved listener tasks and the HTTP client into the `watch` lifecycle, removing the explicit `close` method.
- **kiapi**: Reworked the relay verification scripts to issue requests through `Relay.request` via the relay registry factories, removing the duplicated transport client in `scripts/relay/_client.py`.
- **kiapi**: Converted the repository into a uv workspace and moved the `kiapi` package to `packages/kiapi/` with a `src/` layout. Packaging and lint/test paths are now per-package.
- **kiapi**: Extracted the relay subsystem into a separate `kiapi-relay` package. `kiapi.core.relay` is now `kiapi_relay`, and `kiapi.relay.{local,gcp}` are now `kiapi_relay.{local,gcp}`. The `relay-gcp` extra now pulls `kiapi-relay[gcp]`.
