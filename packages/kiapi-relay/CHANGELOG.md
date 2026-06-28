# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Added a `name` attribute to the `Relay` protocol, populated by the relay
  registry through a `factory_wrapper`. Relay implementations now share a
  `BaseRelay` base class that provides it. `RelayRunner.status()` returns a new
  `RelayHealth` view (`name`, `running`, `failed`) so the active relay can be
  inspected.
- Initial release of `kiapi-relay`, extracted from `kiapi`. Provides the relay
  protocol, request/response schemas, the in-process `RelayRunner`, and the relay
  request client, plus the local filesystem (`kiapi_relay.impl.local`) and GCP
  (`kiapi_relay.impl.gcp`, available via the `gcp` extra) relay backends.
