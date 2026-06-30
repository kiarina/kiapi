# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Added a `kiapi_proxy.core.app` user-directory module (app name `kiapi-proxy`).
  At startup the proxy resolves a persistent relay `node_id` from its user data
  directory and injects it into the relay, and acquires a single-instance lock
  under that directory so a second `kiapi-proxy` cannot share the same node
  identity. Added a `platformdirs` dependency for resolving the data directory.
- Initial release of `kiapi-proxy`: a proxy server that forwards incoming HTTP
  requests to a kiapi instance over a relay (`kiapi-relay`) and returns the
  result. Supports JSON responses, file/binary responses, and chat
  `text/event-stream` responses re-emitted as Server-Sent Events. Ships a
  `kiapi-proxy` CLI and does not depend on `kiapi` or MLX, so it runs on Linux,
  Windows, and resource-constrained machines.
