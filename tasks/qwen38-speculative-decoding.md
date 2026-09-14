# Qwen3.8 の投機的デコードを chat に組み込む

## 背景

mlx-vlm 0.7.1 には投機的デコード（`mlx_vlm/speculative/`）があり、Qwen3.8 では native MTP
（`qwen3_5_mtp`、重み `mlx-community/Qwen3.8-27B-MTP-4bit`）と DFlash2
（drafter `z-lab/Qwen3.8-27B-DFlash2`、README 上は約 2 倍以上）が使える。
2026-09-15 に mlx-vlm を 0.7.1 へ上げた時点では未着手（その時の相談で、上げ終えてから別作業にすると決めた）。

## やること

- kiapi は `generate` / `stream_generate` を直接呼んでいるので、drafter の読み込みと
  `draft_model` / `draft_kind` の受け渡しを `qwen3_5` handler に組み込む
- サーバー機で速度（token/s）と出力の一致を実測し、chat の full verify で確認する
- メモリ（drafter 分）と既定で有効にするかを決める
