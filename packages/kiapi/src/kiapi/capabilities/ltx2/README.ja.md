# ltx2

[English](README.md) | **日本語**

[mlx-video LTX-2](https://github.com/Blaizzy/mlx-video) で、短尺動画生成機能を提供します。

- **T2V**: テキストから動画を生成
- **I2V**: 画像を最初または最後のフレームとして動画化
- **A2V**: 音声でモーションやタイミングを駆動
- **T2V + Audio**: 動画とあわせて音声を生成

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/video/ltx2/generate` | 動画生成 | JSON body と任意の `image` / `end_image` / `audio` FileRef から MP4 を生成。 |
| `GET /v1/video/ltx2/models` | モデル一覧 | 利用可能なモデルの一覧を返す。 |
| `GET /v1/video/ltx2/openapi.json` | OpenAPI | 詳細な入出力仕様、使い方、TIPS を返す。 |

推論されるモード:

| 入力 | モード |
|---|---|
| ファイル添付なし | T2V — テキストから動画 |
| `image` FileRef | I2V — 最初のフレームをアニメ化 |
| `image` + `end_image` FileRef | I2V — 最初と最後のフレームを指定 |
| `end_image` FileRef | I2V — 最後のフレームを指定 |
| `audio` FileRef | A2V — 音声でモーション/タイミングを駆動 |
| `image` + `audio` FileRef | A2V + I2V |
| `generate_audio: true` | T2V + Audio — 音声も生成 |

- `mode: "sync"` は完了まで待ち、単一成果物なら既定で生の MP4 バイト列を返します。
  Job JSON が欲しい場合は `Accept: application/json` を付けます。
- `mode: "async"` は `202` と `{job_id}` を返します。
  `GET /v1/jobs/{job_id}` で進捗を確認し、完了後に `result.file_id` または
  `artifacts[0]` で MP4 を取得します。
- `audio` ファイルと `generate_audio: true` は排他です。

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/video/ltx2/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/video/ltx2/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/video/ltx2/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mlx-video](https://github.com/Blaizzy/mlx-video) | MIT | LTX-2 distilled パイプラインを MLX 上で実行。`pyproject.toml` では既知良好な git commit にピンしている。 |

## Models

| Model | License | Terms | Size | Description |
|---|---|---|---:|---|
| [prince-canuma/LTX-2-distilled](https://huggingface.co/prince-canuma/LTX-2-distilled) | [LTX-2 Community License Agreement](https://huggingface.co/Lightricks/LTX-2/blob/main/LICENSE)（派生元 [Lightricks/LTX-2](https://huggingface.co/Lightricks/LTX-2) に準拠。repo 自体は model card / LICENSE 未記載） | HF gated なし。ただし使用・配布によりライセンス同意 | 101 GB | `distilled`（デフォルト）。2 段 distilled パイプライン。CFG なし、内部約 11 ステップ。呼び出しごとにロード/解放する transient モデル。 |

主な既定値と上限:

| 項目 | 既定値 | 制約 |
|---|---:|---|
| `width` | `512` | 正の 64 の倍数。上限 `768`。 |
| `height` | `512` | 正の 64 の倍数。上限 `768`。 |
| `num_frames` | `97` | `1 + 8*k`。上限 `721`。 |
| `fps` | `24` | 正の整数。 |
| `image_strength` | `1.0` | `0.0..1.0`。I2V の入力フレームへの拘束度。 |

`duration = num_frames / fps` です。24 fps では `97` が約 4 秒、`161` が約 6.7 秒、
`241` が約 10 秒、`481` が約 20 秒、`721` が約 30 秒です。

## Notes

- **transient モデル**:
  LTX-2 は常駐モデルではありません。呼び出しごとにロード・生成・解放し、実行前に
  `memory.reserve()` で約 40 GB の一時メモリ予算を確保します。そのため `/health` の
  resident model には残りません。
- **レスポンス形式**:
  sync で MP4 が 1 つだけ生成される場合、既定では生の MP4 を返します。
  `X-Kiapi-File-Id` / `X-Kiapi-Job-Id` ヘッダから metadata を辿れます。
  `Accept: application/json` を付けると Job JSON を返します。
- **distilled は negative guidance を持たない**:
  classifier-free guidance がないため、negative prompt や `no zoom` / `don't ...`
  のような抑制指示は効きません。避けたいものではなく、欲しい動き・構図・質感を
  書き、seed や `image_strength` で調整します。
- **I2V の `image_strength`**:
  `1.0` は入力フレームに強く固定されます。はっきり動かしたい場合は `0.7` 前後まで
  下げると変化を許しやすくなります。
- **進捗**:
  mlx-video はステップ単位の進捗コールバックを公開していません。kiapi は
  `progress_eta_base_s` を基準に、フレーム数と解像度でスケールした時間ベースの
  synthetic progress を流します。
- **依存更新時の注意**:
  `mlx-video` は API が変わりやすいため git commit にピンしています。更新時は
  `_models/ltx2.py` の `generate_video` 呼び出しと `PipelineType.DISTILLED` の経路を
  確認し、`make verify-ltx2` で実機検証してください。

## Quickstart

### generate — T2V

```bash
PARAMS=$(
jq -n \
--arg prompt "a cat walking through tall grass, sunny, shallow depth of field" \
'{
  model: "distilled",
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  num_frames: 97,
  fps: 24,
  seed: 1
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ltx2.mp4
```

Job JSON が欲しい場合:

```bash
PARAMS=$(
jq -n \
--arg prompt "a small paper boat floating on a quiet pond, gentle ripples" \
'{
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  num_frames: 97,
  seed: 2
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" | jq .
```

### generate — I2V

最初のフレームに使う画像を Files API にアップロードして参照します。

```bash
IMAGE_ID=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@first_frame.png;type=image/png" | jq -r .file_id)

PARAMS=$(
jq -n \
--arg image "$IMAGE_ID" \
--arg prompt "gentle wind, leaves moving, soft cinematic motion" \
'{
  mode: "sync",
  prompt: $prompt,
  image: {type: "file_id", file_id: $image},
  num_frames: 97,
  image_strength: 0.7,
  seed: 3
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ltx2-i2v.mp4
```

最初と最後のフレームを指定する場合:

```bash
IMAGE_ID=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@first_frame.png;type=image/png" | jq -r .file_id)
END_IMAGE_ID=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@last_frame.png;type=image/png" | jq -r .file_id)

PARAMS=$(
jq -n \
--arg image "$IMAGE_ID" \
--arg end_image "$END_IMAGE_ID" \
--arg prompt "a smooth transition from morning to sunset" \
'{
  mode: "sync",
  prompt: $prompt,
  image: {type: "file_id", file_id: $image},
  end_image: {type: "file_id", file_id: $end_image},
  num_frames: 97,
  image_strength: 0.8,
  end_image_strength: 0.8,
  seed: 4
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ltx2-first-last.mp4
```

### generate — A2V

音声ファイルを Files API にアップロードして参照すると、音声がモーションやタイミングを駆動し、
出力 MP4 にミックスされます。

```bash
AUDIO_ID=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@drums.wav;type=audio/wav" | jq -r .file_id)

PARAMS=$(
jq -n \
--arg audio "$AUDIO_ID" \
--arg prompt "a drummer on stage, energetic performance, stage lighting" \
'{
  mode: "sync",
  prompt: $prompt,
  audio: {type: "file_id", file_id: $audio},
  width: 512,
  height: 512,
  num_frames: 97,
  seed: 5
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ltx2-a2v.mp4
```

### generate — T2V + Audio

音声ファイルを使わず、動画と一緒に音声を生成します。

```bash
PARAMS=$(
jq -n \
--arg prompt "a tiny robot dancing in a neon room, playful electronic beat" \
'{
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  num_frames: 97,
  generate_audio: true,
  seed: 6
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ltx2-audio.mp4
```

### async

```bash
PARAMS=$(
jq -n \
--arg prompt "a cinematic shot of clouds moving over a mountain lake" \
'{
  mode: "async",
  prompt: $prompt,
  width: 512,
  height: 512,
  num_frames: 97,
  seed: 7
}'
)

JOB=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/video/ltx2/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" | jq -r .job_id)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```

完了後、Job の `artifacts[0]` または `result.file_id` を使って MP4 を取得します。

```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o ltx2-async.mp4
```
