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

## 関連する上流 PR（2026-09-15 に提出）

- [#2257](https://github.com/Blaizzy/mlx-vlm/pull/2257): Omni の image + video 同時入力。1 引数 `mx.where` /
  `mx.scatter` が mlx 0.32 に無く落ちる問題に加え、joint の位置を使って各 modality の embeds から
  `take` していたため、video の行が範囲外から読まれていた。参照実装どおり各 modality の embeds 全体を
  自分の位置へ代入する形に直した → マージされたら patch C を外す
- [#2258](https://github.com/Blaizzy/mlx-vlm/pull/2258): `load_audio` が stereo を channel 軸で resample する
  （48 kHz stereo が 48,000 samples のまま 16 kHz 扱いになる）。mono 化してから resample する形に直した
  → マージされたら patch B を外せる

## 申し送り

- kiapi の patch C は 2026-09-15 に #2257 と同じ処理へ置き換え済み（`ensure_omni_image_video_join.py`）
- patch A（音声をパスで渡すと落ちる）は 0.7.1 では再現しない。ただし kiapi は B の回避のため自前で
  mono 化・resample した配列を渡しているので、A と B は #2258 のリリース後にまとめて外せる
