# kiapi Architecture

kiapi is a uv workspace for a local inference server. This document is the map
of the architecture; detailed design notes live under
[`docs/concepts`](docs/concepts/).

## Design Principles

- Source code follows
  [Crystal Architecture](https://github.com/kiarina/crystal-architecture).
- Configuration uses
  [Pydantic Settings Manager](https://github.com/kiarina/pydantic-settings-manager).
- All inference is serialized through one worker so memory accounting and MLX
  thread affinity remain predictable.
- Models, subprocess-backed capabilities, jobs, and files use shared lifecycle
  abstractions across every capability.

## Concepts

| Concept | Description |
|---|---|
| [Application](docs/concepts/application.md) | Workspace structure, application startup, settings, and user directories |
| [Model Lifecycle](docs/concepts/model-lifecycle.md) | Setup resources, model registry, memory budget, TTL, and subprocess isolation |
| [Jobs and Files](docs/concepts/jobs-and-files.md) | Processing flow, worker serialization, progress, files, and response negotiation |
| [API](docs/concepts/api.md) | Endpoint organization, model discovery, and two-layer OpenAPI documentation |

## Documentation Types

- [`docs/concepts`](docs/concepts/) explains how the system is designed.
- [`docs/runbooks`](docs/runbooks/) contains operational and incident procedures.
- [`docs/playbooks`](docs/playbooks/) contains repeatable development workflows.
