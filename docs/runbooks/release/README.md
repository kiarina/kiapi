# Release

**English** | [日本語](README.ja.md)

## Prepare

Add release notes to the `Unreleased` section of the root `CHANGELOG.md` and
each changed package's `CHANGELOG.md`.

Then prepare the release:

```bash
mise run release:bump-version <version>
mise run ci --no-setup
```

Review the changes. Only packages with unreleased changes are bumped and
released.

## Publish

Commit the prepared release, then create and push the shared version tag:

```bash
git add VERSION CHANGELOG.md packages/*/pyproject.toml packages/*/CHANGELOG.md uv.lock
git commit -m "chore(release): prepare v<version>"
git tag v<version>
git push origin main --tags
```

The tag starts the release workflow, which creates a GitHub Release and
publishes the selected packages to PyPI.

## Verify

Confirm that the `Release PyPI` workflow succeeded, then check the GitHub
Release and the released packages on PyPI.
