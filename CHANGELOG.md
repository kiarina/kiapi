# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Added a `request` method to the `Relay` protocol and implemented it on `LocalRelay` and `GCPRelay`, promoting the relay request client from the verification scripts into the relay packages. Responses are returned as `RelayResponse`, with binary bodies materialized to a temporary file the caller owns.
- Added a `source_node_id` relay setting to identify the client when issuing relay requests, and a `request_poll_interval_s` setting for GCP request polling.

### Changed

- Simplified the `Relay` protocol to a single `watch` method and moved listener tasks and the HTTP client into the `watch` lifecycle, removing the explicit `close` method.
- Reworked the relay verification scripts to issue requests through `Relay.request` via the relay registry factories, removing the duplicated transport client in `scripts/relay/_client.py`.

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
