# Verifying dependency and patch changes

How to change a model engine (mlx-vlm, mflux, mlx-audio, …), a pinned version, or a
capability's compatibility patch without shipping an unverified combination.

## Work in a git worktree

`kiapi` is an editable install, so a running kiapi executes whatever source is in
the checkout it was installed from. Uncommitted work in that checkout goes live on
the next restart, verified or not. Do the work in a separate worktree with its own
environment:

```sh
git worktree add --detach ../kiapi-wip HEAD
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

Stage explicit paths in the worktree so the `tests/assets` symlink is not included,
then apply the diff to the main checkout:

```sh
git -C ../kiapi-wip add CHANGELOG.md pyproject.toml uv.lock src tests/capabilities
git -C ../kiapi-wip diff --cached HEAD > /tmp/change.patch
git apply --index /tmp/change.patch
```

If `git apply` fails, it can leave files partly written. A half-written `uv.lock`
no longer matches `pyproject.toml`, and the next `uv run` silently re-resolves it to
newer versions than the ones you verified. After moving the change, confirm the lock
is byte-identical to the verified one (`cmp`) before syncing and committing.
