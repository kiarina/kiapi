# mlx-vlm を 0.7.2 以降へ上げて Omni の互換 patch を外す

## 背景

kiapi の公開依存は `mlx-vlm==0.7.1` のままで、0.7.1 の Qwen3-Omni の不具合を次の patch で回避している
（開発環境は prefix 再利用の fork を `tool.uv.sources` で pin しており、そこでは C は no-op、H は skip になる）。

- patch H（`src/kiapi/capabilities/chat/_operations/ensure_omni_deepstack_window.py`）: chunked prefill の
  deepstack が GPU バッファの外へ書き込む（上流 issue #2099）
- patch C（`ensure_omni_image_video_join.py`）: image + video 同時入力で落ちる・範囲外を読む
- patch B（`_utils/load_audio_mono.py` での自前の mono 化・resample）: `load_audio` が stereo を channel 軸で resample する。
  patch A（音声をパスで渡すと落ちる）は 0.7.1 では再現しないが、B の回避で配列を渡しているので B と一緒に外せる

上流で 3 件とも直り、どれも mlx-vlm 0.7.2（2026-09-21）に入った（2026-09-28 に `git tag --contains` で確認。最新は 0.7.3）。

- H: 自分の PR #2256 は close され、上流の `22a84f63`（#2265）で修正
- C: 自分の PR #2257 は close され、上流の #2287（`bd6d8ca0`）で修正
- B: 自分の PR #2258 がマージ

## やること

- `pyproject.toml` の `mlx-vlm==0.7.1` を 0.7.2 以降へ上げる。pin 中の fork（`6581ba8c`）の base `e79b0e04` は 0.7.2 に
  含まれるが、0.7.3 まで上げるなら fork を rebase して pin を更新するかも決める（prefix 再利用の PR は
  `waiting/mlx-vlm-prefix-reuse-prs.md` で待っている）
- patch H・C・B（と A の回避）と、その test を削除する
- chat の full verify（`mise run verify --kiapi --family chat`）で Omni の画像・動画・音声を確かめる
- `CHANGELOG.md` の `Unreleased` に追記する
