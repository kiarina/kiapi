# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Added an optional plugin-based remote job relay with Firebase Realtime Database notifications, GCS request/response payloads, in-process ASGI dispatch, committed-response recovery, and atomic terminal delivery.

### Fixed

- Added the OAuth scopes required by the Firebase Realtime Database REST API to GCP relay credentials.

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
