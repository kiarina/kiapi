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
# Install all workspace packages and dev tooling
uv sync --all-groups --all-extras

# Format, lint, generate config template and API docs
make

# Run unit tests across all packages
make test
```

Each package is versioned and released independently. See each package's
`CHANGELOG.md` and the [Releasing](#releasing) section.

## Releasing

Releases are per-package and triggered by pushing a tag named `<package>-v<version>`:

```bash
make bump-version PKG=kiapi VERSION=0.2.1
# review the diff, then:
git add packages/kiapi/pyproject.toml packages/kiapi/CHANGELOG.md uv.lock
git commit -m "chore(release): prepare kiapi-v0.2.1"
git tag kiapi-v0.2.1 && git push origin main --tags
```

## License

MIT
