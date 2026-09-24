# Qwen3.8-Flash-Next でも画像追加時に既存prefixを再利用する

## 背景（2026-09-24）

本番で実測した Flash-Next（`qwen4_exp`）の APC: 同一 request の再送と、同じ画像のままのテキスト追加は再利用する
（1000/1001、1000/1048）が、画像を 1 枚追加すると全量 prefill（0/1333）。Qwen3.8-27B は同じ操作で 1046/1332 を再利用する。
長い会話の途中で画像を足すと、それまでの全体を読み直す（Flash-Next の prefill は約 550 tok/s なので 50K tokens で約 1.5 分）。

27B の画像追加時の再利用は、mlx-vlm fork の `apc_images.ImagePrefixContext`（上流 PR #2309、OPEN・review 待ち）と、
kiapi の `qwen3_5` handler の `apc_image_prefix=True`（`params.model == "qwen3.8-27b"` に限定）で実現している。

## 見立て

- `qwen4_exp.Model` は `qwen3_5.Model` を継承し、vision tower（Qwen3-VL）と `get_input_embeddings`・`get_rope_index` も
  継承している。fork が `qwen3_5.py` に入れた「復元した prefix の position_ids / rope_deltas を使う」変更も、そのまま効くはず
- Flash-Next が対象外なのは、`ImagePrefixContext.prepare` の `config.model_type != "qwen3_5"` という gate と、
  kiapi 側の model 名の限定だけ
- Flash-Next 固有で確認が要るのは、checkpoint に入る状態が正しく復元されること:
  QSA の KV cache（`QSAKVCache`）、Gated DeltaNet の状態、n-gram 埋め込みの token 履歴（cache の `update_window`）。
  text の APC は上流の実装で `qwen4_exp` にも効いているので、仕組みとしては揃っている見込み

## やること

- mlx-vlm fork（`kiarina/mlx-vlm`、branch `codex/qwen38-image-prefix-reuse`）で gate を `qwen4_exp` に広げる。
  image prefix の schema 名（`qwen3_5-v1`）を model type ごとに分けるか決める
- fork の tests に `qwen4_exp` の小さな config を足し、画像追加・旧画像の差し替え・text only を確認する。
  量子化 MoE は prefill の形で logits が完全一致しないので、27B のときと同じく色や合言葉の順序で cold / hit の一致を見る
- 上流 PR #2309 へ追加するか、別 PR にするかを決める（#2309 は review 待ちなので、範囲を広げると review が重くなる）
- kiapi の `qwen3_5.run` の `image_prefix_enabled` を Flash-Next にも有効にし、pin を更新して chat の full verify を通す
- 本番で上の実測をやり直し、画像追加で再利用されることを HISTORY に記録する

## 完了条件

- Flash-Next で画像を追加したとき、変わっていない前半が再利用され、chat の full verify が通る
