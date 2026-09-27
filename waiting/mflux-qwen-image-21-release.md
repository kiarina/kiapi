# mflux#741（Qwen-Image-2.1 編集）を含む mflux のリリース

- 待っているもの: [mflux-community/mflux#741](https://github.com/mflux-community/mflux/pull/741) を含む mflux の PyPI リリース。
  #741 は 2026-09-27 にマージ済み（merge commit `acdfc98`）。PyPI の最新は 0.20.0 のまま（2026-09-28 確認）
- 確かめ方: `curl -s https://pypi.org/pypi/mflux/json | jq -r .info.version` が 0.20.0 より新しいか。新しければ fork の checkout
  （`~/src/github.com/kiarina/mflux`、`upstream` remote）で `git fetch upstream --tags && git tag --contains acdfc98`
- 確かめる目安: 2026-10-05
- 満たされたら: Qwen-Image-2.1 の pin を上流へ戻すタスクを起こす
  - `pyproject.toml` の `[tool.uv.sources]` の mflux 行を外し、`mflux>=<その版>` にする
  - マージ版は kiapi が pin している PR head `144a6be` から rebase・修正されている。import 先
    （`mflux.models.qwen21.reference.QwenImage21Edit`）と `generate_image` の引数（`image_paths`、`output_resolution`、
    `use_kv_cache`）が変わっていないか確かめる。報告した循環 import はマージ版で `reference/__init__.py` の遅延 re-export に
    なっているので、import を variant の module へ戻すかも決める
  - qwen の full verify（`mise run verify --kiapi --family qwen`、image-2.1 は [9]〜[12]）と、mflux を使う zimage / flux2 /
    ernie / ideogram4 / seedvr2 の full verify を通す
  - fork の `qwen-image-2.1-edit` branch（force-push しない）を消すのは、旧 kiapi を入れ直す可能性が無くなってから
- 経緯: `HISTORY.md` の 2026-09-25（image-2.1 の追加と実測）と 2026-09-28
