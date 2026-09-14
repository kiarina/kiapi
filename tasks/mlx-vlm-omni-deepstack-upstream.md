# 上流で Omni の deepstack 修正が出たら patch H を外す

## 背景

mlx-vlm 0.7.1 の Qwen3-Omni は、chunked prefill で deepstack の入力を chunk に切り出さず、長い画像・
動画プロンプトで GPU バッファの外へ書き込む（上流 issue #2099）。kiapi は patch H
（`src/kiapi/capabilities/chat/_operations/ensure_omni_deepstack_window.py`）で回避している。
同じ修正を上流へ PR [Blaizzy/mlx-vlm#2256](https://github.com/Blaizzy/mlx-vlm/pull/2256) として出した
（2026-09-15、fork: kiarina/mlx-vlm、branch `fix/qwen3-omni-deepstack-chunked-prefill`）。

## やること

- #2256 のレビューに対応する（指摘があれば fork の branch に追加 commit）
- マージされたリリースへ mlx-vlm を上げ、patch H と test を削除し、chat の full verify で確認する

## 申し送り

- PR の「Not in this PR」に、別の上流の問題を 2 点書いた。kiapi はどちらも patch で回避済み:
  image + video 同時入力の 1 引数 `mx.where` / `mx.scatter`（patch C）と、stereo 音声の resample（patch B）
