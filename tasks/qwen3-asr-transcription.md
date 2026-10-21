# Qwen3-ASR で文字起こしの family を足し、声の登録の書き起こしに使う

## 背景

kiapi には音声を文字にする口が無い。speech の声の登録（`POST /v1/audio/voices`）は transcript が無いと話者の埋め込みだけで
まねるので似なくなり（`src/kiapi/capabilities/speech/README.md`）、今は呼ぶ側が書き起こしを用意している。

固定している `mlx-audio==0.6.0` に `mlx_audio.stt.models.qwen3_asr`（Qwen3-ASR 0.6B・1.7B）と
`qwen3_forced_aligner`（単語の時刻）がすでに入っているので、依存を増やさずに足せる。

範囲は次の 2 つ（2026-10-22、kiarina）。

- ファイルの文字起こし: OpenAI 互換の `POST /v1/audio/transcriptions`（長い録音・動画の音・字幕）
- 声の登録の書き起こし: `transcript` を省いた登録で、参照の音声を ASR で書き起こして使う

リアルタイムの聞き取り（Spirits Garden の body の発話ごとの文字起こし）は範囲外。端末の OS の音声認識（pcm_asr）が
Mac・Windows の GPU で CER 0%・約 100 ms で、kiapi は推論を 1 本のワーカーで順番に処理するので chat・speech と同じ列で遅れが読めない。

## やること

1. MLX 版の質を確かめる。speech では mlx-audio の既定（繰り返しの罰則・プロンプトの並べ方）が本家とずれて質が落ちた。
   labs の `docs/mlx-port-parity.md` の型で、本家の PyTorch（qwen-asr）と同じ音声の出力を比べる
2. 日本語の精度と速さを測り、既定のモデルを決める。labs `2026/10/19/flutter-pcm-asr-plugin` の 6 区間の日本語の fixture で、
   0.6B・1.7B（8bit と bf16）の CER と処理時間を測り、whisper large-v3-turbo の値（同 lab）と並べる
3. モデルのライセンスと利用条件をモデルカードで確かめ、README の Models の表に書く
4. family を足す（名前は既存の family にならう。`docs/` と `ARCHITECTURE.md` の family の足し方を先に読む）
   - `POST /v1/audio/transcriptions`: `file`・`model`・`language`・`response_format`（`json`・`text`・`verbose_json`）・
     `timestamp_granularities`（`segment`・`word`。`word` は forced aligner）。OpenAI と違うところは README の Notes に書く
   - `GET .../models` と `openapi.json` は speech と同じ形
5. speech の声の登録で `transcript` が無ければ書き起こして保存し、返す voice に書き起こした transcript を含める
   （呼ぶ側が見て直せるように）。無効にする設定を置くかは実装のときに決める
6. `mise run ci` と、足した family と speech の full verify を通す。verify はサーバー機の稼働中のサービスを止めるので、
   kiarina に時間を確かめてから行う。`CHANGELOG.md` の `Unreleased` と README の Resources の表に追記する

## 未決

- 書き起こしの列: 長いファイルを 1 件で処理すると chat・speech を長く待たせる。区切って順番に処理するか、上限を置くか
