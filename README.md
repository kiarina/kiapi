<!-- Language: **English** | [日本語](README.ja.md) -->

# kiapi workspace

[English](README.md) | [日本語](README.ja.md)

This repository is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/) that hosts the kiapi family of packages.

## Packages

| Package | Description | Runs on |
| --- | --- | --- |
| [`kiapi`](packages/kiapi/README.md) | Unified local inference API server for LLM agents on Apple Silicon (MLX): chat, embedding, image, music, sound-effect, and video. | Apple Silicon (macOS) |
| [`kiapi-relay`](packages/kiapi-relay/README.md) | Shared relay transport (request/response schemas and client) used to reach a kiapi instance over a relay. | Any platform |
| [`kiapi-proxy`](packages/kiapi-proxy/README.md) | Proxy server that forwards HTTP requests to a kiapi instance over a relay and returns the result (JSON, files, and chat event streams). | Linux / Windows / macOS |

`kiapi` requires capable Apple Silicon hardware. `kiapi-proxy` lets clients on any
platform reach a remote kiapi through a relay, so it is published as a separate
package that does not pull in the heavy MLX dependencies.

## Development

```bash
# Install tools, workspace dependencies, and test assets
make init

# Format, lint, generate config template and API docs
make

# Run unit tests across all packages
make test
```

The Makefile is a thin wrapper around mise tasks. Use `mise run <task> --help`
for package selection and task-specific options, such as
`mise run test kiapi-relay` or `mise run format --unsafe`.

The whole workspace shares a single version, tracked in the root `VERSION`
file. The root `CHANGELOG.md` records project-wide notes; each package keeps its
own `CHANGELOG.md`. See the [Releasing](#releasing) section.

## Releasing

Releases use one shared version and a single `v<version>` tag. `bump-version`
detects every package that has unreleased changelog entries and bumps only those
to the new version; packages without changes keep their current version.

```bash
mise run release:bump-version 0.3.0
# review the diff, then:
git add VERSION CHANGELOG.md packages/*/pyproject.toml packages/*/CHANGELOG.md uv.lock
git commit -m "chore(release): prepare v0.3.0"
git tag v0.3.0 && git push origin main --tags
```

Pushing the tag triggers the release workflow, which builds the selected
packages, creates a single GitHub Release from the root `CHANGELOG.md`, and
publishes the artifacts to PyPI.

## License

MIT
