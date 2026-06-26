# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Initial release of `kiapi-relay`, extracted from `kiapi`. Provides the relay
  protocol, request/response schemas, the in-process `RelayRunner`, and the relay
  request client, plus the local filesystem (`kiapi_relay.local`) and GCP
  (`kiapi_relay.gcp`, available via the `gcp` extra) relay backends.
