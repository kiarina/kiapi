# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Relay participants now derive a stable `node_id` from a data directory via
  `get_or_create_node_id`, guarded by a `SingleInstanceLock` (cross-platform
  filesystem lock backed by `filelock`) so a second process cannot reuse the
  same identity and double-consume work. Both are exported from `kiapi_relay`.
- Added liveness-based node discovery. A serving node publishes a heartbeat
  under `{prefix}/liveness/{node_id}` on `heartbeat_interval_s` (default `300`)
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
