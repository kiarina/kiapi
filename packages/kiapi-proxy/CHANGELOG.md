# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Initial release of `kiapi-proxy`: a proxy server that forwards incoming HTTP
  requests to a kiapi instance over a relay (`kiapi-relay`) and returns the
  result. Supports JSON responses, file/binary responses, and chat
  `text/event-stream` responses re-emitted as Server-Sent Events. Ships a
  `kiapi-proxy` CLI and does not depend on `kiapi` or MLX, so it runs on Linux,
  Windows, and resource-constrained machines.
