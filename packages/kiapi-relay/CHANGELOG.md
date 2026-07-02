# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Changed

- The `gcp:setup` task no longer passes `--scopes` to
  `gcloud auth application-default login`. The default ADC scopes already
  include `cloud-platform`, which covers the GCS and RTDB access the relay
  needs, so the extra scopes were unnecessary.
- The `gcp:setup` Impersonation method now runs
  `gcloud auth application-default login` itself instead of only reminding the
  user to, since ADC is the base credential the impersonation chain mints SA
  tokens from. It then grants `roles/iam.serviceAccountTokenCreator` to the
  actual ADC principal (resolved via userinfo) rather than the active gcloud
  CLI account, so the binding is correct even when the two credential stores
  hold different accounts.

## [0.3.0] - 2026-07-02

### Added

- Added a `gcp:setup` mise task (run from the `kiapi-relay` package directory)
  that interactively provisions the GCS bucket, Firebase Realtime Database
  instance, and authentication for `GCPRelay`, then prints the kiapi YAML to
  paste with `kiapi config edit`. Existing buckets and RTDB instances are
  detected and left untouched, so the task is safe to re-run. It relies on the
  project-local `firebase-tools` installed by `mise run setup`. The task
  verifies `firebase-tools` has its own login (via `firebase login:list`)
  instead of relying on `firebase projects:list`, which also succeeds through
  the Application Default Credentials fallback and then fails the Realtime
  Database calls with a quota-project 403; the RTDB creation failure message
  now points at `firebase-debug.log` and lists both the missing-login and
  Blaze-plan causes. The GCP relay README was rewritten around this task.

- Relay participants now derive a stable `node_id` from a data directory via
  `get_or_create_node_id`, exported from `kiapi_relay`. Single-instance locking
  (preventing a second process from reusing the same identity) is provided by
  the shared `kiarina-utils-app` package rather than `kiapi_relay`.
- Added liveness-based node discovery. A serving node publishes a heartbeat
  under `liveness/{node_id}` on `heartbeat_interval_s` (default `300`)
  as part of the `watch` lifecycle, and removes it on clean shutdown.
  `Relay.request` selects the most recently seen node within `liveness_ttl_s`
  (default `1800`) and fails with `no_relay_node` when none has reported in that
  window. Added a `node_id` attribute to the `Relay` protocol (set by the host
  application) alongside `heartbeat_interval_s` and `liveness_ttl_s` settings on
  the local and GCP backends.
- Added a `name` attribute to the `Relay` protocol, populated by the relay
  registry through a `factory_wrapper`. Relay implementations now share a
  `BaseRelay` base class that provides it. `RelayRunner.status()` returns a new
  `RelayHealth` view (`name`, `running`, `failed`) so the active relay can be
  inspected.
- Initial release of `kiapi-relay`, extracted from `kiapi`. Provides the relay
  protocol, request/response schemas, the in-process `RelayRunner`, and the relay
  request client, plus the local filesystem (`kiapi_relay.impl.local`) and GCP
  (`kiapi_relay.impl.gcp`, available via the `gcp` extra) relay backends.
