# chat の出力上限を呼び出し側の指定と context window で決める

## 背景

chat の出力トークン数は、request の `max_completion_tokens`（省略時 `default_max_tokens`=512）を
`max_tokens_cap`（`KIAPI_CHAT_MAX_TOKENS_CAP`、既定 4096）で切り詰めて決めている
（`src/kiapi/capabilities/chat/_operations/resolve_chat_params.py`）。この cap は initial commit から
あり、single worker queue を長時間塞がないためのサーバー全体の保護で、モデルの性質とは関係ない。
思考や長いコード生成では 4096 で切れやすい。

2026-09-16 にユーザーと合意した方針:

- kiapi は個人利用が前提なので、どこまで出力させるかは呼び出し側が決める
- モデル自体に出力専用の上限はなく、真の上限は context window（入力 + 出力）だけ。
  サーバーはそれを知っていて、出力の上限を「context window − 入力トークン数」で動的に決める
- 上限を超える `max_completion_tokens` はエラーにせず切り詰める（OpenAI は 400 だが採らない）
- 生成を切断時に止める処理は今回はやらない（別途判断）

## やること

- `max_tokens_cap` / `KIAPI_CHAT_MAX_TOKENS_CAP` を廃止する
- `default_max_tokens` の既定を 1024 にする
- context window を各モデルの `config.json` から読み込み時に取る（手で書かない）。
  qwen3.8 は `max_position_embeddings` = 262144。Omni は config の構造が違うので、読み方は
  handler ごとに持たせる（未確認）。YaRN などの拡張設定があればそちらを優先する
- 生成ループで「入力トークン数 + 生成数」が context window に達したら止める。入力トークン数は
  mlx-vlm の `stream_generate` が各チャンクに `prompt_tokens` として付けてくる
  （mlx-vlm 0.7.1 `generate/dispatch.py`）。非 stream の経路は `generate()` を 1 回呼ぶだけなので、
  stream と同じループに揃える
- 上限（指定値または context window）で止まったときに `finish_reason: "length"` を返す。
  今は `format_response.py` が tool call 以外で常に `"stop"` を返している
- モデル一覧の API で `context_window` を返し、呼び出し側が事前に確認できるようにする
  （どの endpoint に出すかは実装時に確認）
- CHANGELOG の `Unreleased` に追記する（cap の廃止は設定の破壊的変更）。chat の full verify を通す

## 懸念

- 長い出力で KV キャッシュが増え、`peak_headroom_gb` の見込みを超える可能性がある。長い入力でも
  起きる既存の問題なので今回は扱わない
