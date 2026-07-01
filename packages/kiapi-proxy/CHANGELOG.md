# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Added a `kiapi_proxy.core.app` user-directory module (app name `kiapi-proxy`).
  At startup the proxy resolves a persistent relay `node_id` from its user data
  directory and injects it into the relay, and acquires a single-instance lock
  under that directory so a second `kiapi-proxy` cannot share the same node
  identity. User directories are fully delegated to the shared
  `kiarina-utils-app` package (removing the private `AppSettings`/user-directory
  copy and the direct `platformdirs` dependency); the app identity is set via
  `core.app.configure_app()` from the CLI and the ASGI app. `core.app` keeps
  `AppSettings`, `settings_manager`, and `get_user_{cache,config,data}_dir`, and
  the directory getters return `pathlib.Path`. The user-directory override
  environment variables use the `KIARINA_UTILS_APP_` prefix.
- Initial release of `kiapi-proxy`: a proxy server that forwards incoming HTTP
  requests to a kiapi instance over a relay (`kiapi-relay`) and returns the
  result. Supports JSON responses, file/binary responses, and chat
  `text/event-stream` responses re-emitted as Server-Sent Events. Ships a
  `kiapi-proxy` CLI and does not depend on `kiapi` or MLX, so it runs on Linux,
  Windows, and resource-constrained machines.
