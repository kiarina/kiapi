# Verifying dependency and patch changes

How to change a model engine (mlx-vlm, mflux, mlx-audio, …), a pinned version, or a
capability's compatibility patch without shipping an unverified combination. Use the
same worktree flow for any change that needs a GPU verify, such as adding a model.

## Work in a git worktree

`kiapi` is an editable install, so a running kiapi executes whatever source is in
the checkout it was installed from. Uncommitted work in that checkout goes live on
the next restart, verified or not. Do the work in a separate worktree with its own
environment:

```sh
git worktree add -b wip ../kiapi-wip main
cd ../kiapi-wip
ln -s "$OLDPWD/tests/assets" tests/assets   # gitignored, so not in the worktree
uv sync --inexact
```

Without the `tests/assets` link, the verify scripts stop at the first case that
reads an image, audio, or video asset.

## Check what the lock removes, not only what it adds

After `uv lock`, list the packages that left the lock:

```sh
git diff uv.lock | grep -E '^[-+](name|version) = ' | paste - - | grep '^-name'
```

A package another engine imports without declaring it can disappear with the
dependency that used to pull it in. For example, mlx-vlm 0.7 stopped depending on
`mlx-lm`, while mlx-embeddings' Qwen3-VL model imports `mlx-lm` at module level.
Search the installed engines for imports of each removed package, and declare any
that are still used in `pyproject.toml` with a comment saying who needs it.

## Re-check every patch on an engine bump

Capabilities pin engines exactly when they patch their internals (for chat, see the
patch table in `src/kiapi/capabilities/chat/README.md`). For each patch, check the new
version's source: remove it if upstream fixed the bug, keep it if the bug is still
there, and adapt it if the code it touches moved. Note which case you checked on
device.

## Verify in full, not with `--fast`

`--fast` runs only the first case of each verify script, which is usually plain
text. Image, audio, video, tool calling, and streaming regressions only show up in a
full run of the affected family:

```sh
mise run verify --kiapi --family chat
```

A newly added model needs its weights first; until then its requests return 503
(`not activated`), and verify does not download them:

```sh
uv run kiapi activate --repo <huggingface-repo>
```

When a case crashes the server, the verify driver's server log is
`<tmp>/kiapi-verify-*/kiapi.log`, and a native abort (for example a Metal page
fault) also leaves a crash report in `~/Library/Logs/DiagnosticReports/`.

## Move the verified change back

Commit in the worktree, staging explicit paths so the `tests/assets` symlink is not
included, then fast-forward the main checkout to that commit:

```sh
git -C ../kiapi-wip add CHANGELOG.md pyproject.toml uv.lock src tests/capabilities
git -C ../kiapi-wip commit -m "..."
git pull --ff-only
git merge --ff-only wip
cmp uv.lock ../kiapi-wip/uv.lock
uv sync --inexact
```

Rebase the worktree branch first if `main` moved. Avoid moving the change as a
patch: `git apply` can stop halfway (a `tests/assets` symlink did once), and a
half-written `uv.lock` no longer matches `pyproject.toml`, so the next `uv run`
silently re-resolves it to versions you did not verify. `cmp` confirms the lock is
the verified one. `--inexact` keeps packages installed outside the lock, such as
ltx2's `mlx-video`. Restart the service, then remove the worktree and the branch.

## Verifying on the serving machine

The verify driver stops a running launchd service, serves the worktree on port 8000,
and restarts the service with its installed plist afterwards; it does not repoint the
service at the worktree. Outside the driver, only one kiapi can run on a machine
(`instance.lock` in the user cache directory), so an ad-hoc worktree server needs the
service stopped first.
