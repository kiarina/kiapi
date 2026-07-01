# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- At startup the proxy resolves a persistent relay `node_id` from its user data
  directory (app name `kiapi-proxy`) and injects it into the relay, and acquires
  a single-instance lock so a second `kiapi-proxy` cannot share the same node
  identity. User directories and single-instance locking are provided by the
  shared `kiarina-utils-app` package, used directly (`kiarina.utils.app`); the
  app identity is set by calling `kiarina.utils.app.configure("kiapi-proxy",
  "kiarina")` at the CLI entry point. The single-instance lock is scoped to the
  user cache directory. The user-directory override environment variables use
  the `KIARINA_UTILS_APP_` prefix.
- Initial release of `kiapi-proxy`: a proxy server that forwards incoming HTTP
  requests to a kiapi instance over a relay (`kiapi-relay`) and returns the
  result. Supports JSON responses, file/binary responses, and chat
  `text/event-stream` responses re-emitted as Server-Sent Events. Ships a
  `kiapi-proxy` CLI and does not depend on `kiapi` or MLX, so it runs on Linux,
  Windows, and resource-constrained machines.
