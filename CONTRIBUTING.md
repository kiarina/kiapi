# Contributing to kiapi

Thank you for your interest in kiapi. This is a personal open-source project,
so reviews and support are handled on a best-effort basis.

## Development Setup

```sh
make init
make test
make
```

`make` formats the code, runs lint/type checks, regenerates the full config
template, and rebuilds the API documentation under `public/`.

## Tests

Unit tests live under `tests/` and should mirror the `kiapi/` package structure.
Keep GPU-heavy model loading and inference out of `tests/`.

```sh
make test
```

GPU feature and regression checks live in `scripts/capabilities/verify_*.py` and require a
running kiapi server plus the relevant activated models.

```sh
make verify
make verify-fast
make verify-one
make verify-{capability}
```

## Pull Requests

Before opening a pull request, please run:

```sh
make test
make
make build
```

For bug reports and fixes, include:

- macOS version, Apple Silicon model, and memory size
- Python version and install method
- affected capability and model family
- exact command or request payload
- relevant logs and error output

Commit messages and pull request titles should use Conventional Commits:

```text
type(scope): subject
```

Examples:

```text
fix(chat): handle empty streaming chunks
docs(web): clarify Docker requirement
ci: run release-quality checks on pull requests
```

## Changelog

Update the `Unreleased` section of both the changed package's
`packages/<package>/CHANGELOG.md` and the root `CHANGELOG.md` when a change
affects user-visible behavior, dependencies, features, or deployment/release
pipelines. In the root changelog, prefix package-specific notes with the package
name (e.g. `**kiapi-relay**: ...`); release notes are generated from it.

Documentation-only changes, formatting-only changes, comments, and internal
cleanup do not need a changelog entry unless they affect users.
