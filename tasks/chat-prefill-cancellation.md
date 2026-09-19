# mlx-vlm の長いprefillをclient切断時にキャンセルする

## 背景

2026-09-19にchat client切断をqueued jobと生成token境界の協調キャンセルへ結線した。
ただしmlx-vlm 0.7.1の`stream_generate` / `generate_step`はchunked prefill中のcancel callbackを
公開していない。100K tokens級のcold promptでは、切断してもprefillが最初のtokenを返すまで停止できない。

## やること

- mlx-vlmのchunked prefill loopへthread-safeなcancel callbackを追加する設計を作る
- text、image、audio、video、APC checkpoint、speculative decodingとのcleanupを確認する
- kiapiからcallbackを渡し、2048-token chunk境界など安全な地点で`JobCanceledError`へ変換する
- upstreamへ提案する場合は回帰テスト付きにする
- 25K / 100K tokensで切断からworker解放までの時間を実測する

## 完了条件

- cold prefill中の切断が最初の生成tokenを待たずに安全なchunk境界で停止する
- APC lease、prompt cache、MLX cache、multimodal temporary inputが確実に解放される
- 通常のchat full verifyとdisconnect検証が通る
