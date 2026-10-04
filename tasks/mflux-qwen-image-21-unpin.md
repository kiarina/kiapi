# mflux を 0.21.0 へ上げ、Qwen-Image-2.1 の fork pin を外す

## 背景

Qwen-Image-2.1 の編集（image-2.1）は、上流 PR [mflux-community/mflux#741](https://github.com/mflux-community/mflux/pull/741) の head
`144a6be` を fork（`kiarina/mflux` の `qwen-image-2.1-edit` branch）から `[tool.uv.sources]` で pin して動かしている。
#741 は 2026-09-27 にマージ（merge commit `acdfc98`）され、**mflux 0.21.0 が PyPI に出た**（tag `v.0.21.0`、`f63b4f0`、
2026-10-03。`git tag --contains acdfc98` で含まれることを 2026-10-05 に確認）。`waiting/mflux-qwen-image-21-release.md` から起こした。

0.21.0 の依存は `huggingface-hub<2.0`・`opencv-python<5.0`・`mlx<0.33.0`・`transformers<6.0,>=5.5.0`（0.20.0 と同じ上限）。
hub 2 と opencv 5 の阻害は 0.21.0 でも解けない。

## やること

- `pyproject.toml` の `[tool.uv.sources]` の mflux 行を外し、`mflux>=0.21.0` にする
- マージ版は pin している PR head `144a6be` から rebase・修正されている。import 先
  （`mflux.models.qwen21.reference.QwenImage21Edit`）と `generate_image` の引数（`image_paths`、`output_resolution`、
  `use_kv_cache`）が変わっていないか確かめる。報告した循環 import はマージ版で `reference/__init__.py` の遅延 re-export に
  なっているので、import を variant の module へ戻すかも決める
- worktree で `mise run ci` を通し、qwen の full verify（`mise run verify --kiapi --family qwen`、image-2.1 は [9]〜[12]）と、
  mflux を使う zimage / flux2 / ernie / ideogram4 / seedvr2 の full verify を通す。verify はサーバー機の稼働中サービスを止めるので、
  kiarina に時間を確かめてから行う
- fork の `qwen-image-2.1-edit` branch（force-push しない）を消すのは、旧 kiapi を入れ直す可能性が無くなってから

## 経緯

`HISTORY.md` の 2026-09-25（image-2.1 の追加と実測）、2026-09-28（waiting への切り出し）、2026-10-05
