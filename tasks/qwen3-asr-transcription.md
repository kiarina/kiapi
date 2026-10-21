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

1. モデルは Qwen3-ASR 1.7B だけを入れる（0.6B は入れない。2026-10-22、kiarina）。ライセンスと利用条件をモデルカードで確かめ、
   README の Models の表に書く
2. family を足す（名前は既存の family にならう。`docs/` と `ARCHITECTURE.md` の family の足し方を先に読む）
   - `POST /v1/audio/transcriptions`: `file`・`model`・`language`・`response_format`（`json`・`text`・`verbose_json`）・
     `timestamp_granularities`（`segment`・`word`。`word` は forced aligner）。OpenAI と違うところは README の Notes に書く
   - `GET .../models` と `openapi.json` は speech と同じ形
3. speech の声の登録で `transcript` が無ければ書き起こして保存し、返す voice に書き起こした transcript を含める
   （呼ぶ側が見て直せるように）。無効にする設定を置くかは実装のときに決める
4. `mise run ci` と、足した family と speech の full verify を通す。verify には日本語の音声の書き起こしを入れ、
   正しく文字になるかを確かめる（悪ければ、そこで初めて本家の PyTorch 版との差を疑う）。verify はサーバー機の稼働中のサービスを止めるので、
   kiarina に時間を確かめてから行う。`CHANGELOG.md` の `Unreleased` と README の Resources の表に追記する

## 進捗（2026-10-22、開発機）

- family `transcription` を実装した（`POST /v1/audio/transcriptions`、multipart。`json`・`text`・`verbose_json`、`timestamp_granularities[]`）。
  モデルは `mlx-community/Qwen3-ASR-1.7B-bf16` と aligner の `mlx-community/Qwen3-ForcedAligner-0.6B-bf16` を 1 つの ModelSpec で一緒に読む
  （実測 5.5 GB）。日本語の単語分けに `nagisa` を足した
- `verbose_json` の `segments` は aligner の単語を文に束ねたもの（aligner は句読点を落とすので、文の文字数ぶん単語を取る）。
  aligner の無い言語は decode した部分ごとに 1 つ
- 区切りは 3 分にした（本家の既定は 20 分、時刻を付けるときは 3 分）。20 分の区切りは M1 Max で重みの上に 11.4 GB・実時間の 0.55 倍、3 分は 2.3 GB・0.37 倍だった。区切った文は、スペースを使わない言語ではスペースなしで繋ぐ（本家どおり。mlx-audio は常にスペースで繋ぐ）
- 声の登録で `transcript` が無ければ、切った参照を書き起こして保存する（`KIAPI_SPEECH_TRANSCRIBE_REFERENCE`、既定 on。モデルが未 activate なら警告して従来どおり）
- 長いファイル: 1 時間と 100 MB で上限にした（`KIAPI_TRANSCRIPTION_MAX_AUDIO_SECONDS`・`MAX_FILE_MB`）
- 開発機で TestClient から通した: 14 秒の日本語の会話で json・text・verbose_json（文 9・単語）・エラー・声の登録の自動の書き起こし
- 開発機で `mise run ci`（450 passed）と `mise run verify --kiapi --family transcription`（5/5。`say` の Kyoko で作った日本語を json・text・verbose_json・エラー・声の登録で）を通した。
  OpenAI の Python SDK（`client.audio.transcriptions.create`）で json・text・verbose_json（words つき）が型どおりに読めた
- Web UI の汎用フォームは JSON で送るので multipart のこの口は試せない。`tasks/web-ui.md` に残した

## 残り

- 本番（サーバー機）へ入れる。サービスを止めるので kiarina に時間を確かめる。入れたら `kiapi activate --family transcription`（5.9 GB）、
  M4 Max で README の Measured に数字を足し、このファイルを `HISTORY.md` へ移して消す
