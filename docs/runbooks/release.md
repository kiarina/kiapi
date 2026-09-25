# Release

## Prepare

Add release notes to the `Unreleased` section of `CHANGELOG.md`.

Then prepare the release:

```bash
mise run release:bump-version <version>
mise run ci --no-setup
```

This updates the `version` in `pyproject.toml`, `uv.lock`, and moves the
`Unreleased` notes into a new version entry. Review the changes.

## Publish

Commit the prepared release, then create and push the version tag:

```bash
git add pyproject.toml CHANGELOG.md uv.lock
git commit -m "chore(release): prepare v<version>"
git tag -a v<version> -m v<version>
git push origin main --tags
```

The tag starts the release workflow, which checks that the tag matches the
`pyproject.toml` version, creates a GitHub Release, and publishes `kiapi` to
PyPI.

## Verify

Confirm that the `Release PyPI` workflow succeeded, then check the GitHub
Release and the released package on PyPI.
