# flux2

[English](README.md) | **日本語**

[mflux FLUX.2 Klein](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/flux2/README.md) で、画像生成・画像編集・LoRA 学習機能を提供します。

- **generate**:
  - txt2img / img2img
- **edit**:
  - Files API の 1 枚以上の参照画像を使う複数参照編集
- **train**:
  - 自前データセット ZIP から LoRA アダプタを学習

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/flux2/generate` | 画像生成 | プロンプトから画像を生成。`init_image` FileRef がある場合は img2img。 |
| `POST /v1/image/flux2/edit` | 画像編集 | Files API の `images` FileRef 配列を参照画像として編集。 |
| `POST /v1/image/flux2/train` | LoRA 学習 | データセット ZIP から LoRA アダプタを学習。**常に async**。 |
| `GET /v1/image/flux2/models` | モデル一覧 | 利用可能なモデルの一覧を返す。 |
| `GET /v1/image/flux2/openapi.json` | OpenAPI | 詳細な入出力仕様、使い方、TIPS を返す。 |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/flux2/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/flux2/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/flux2/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/filipstrand/mflux) | MIT | FLUX.2 Klein の生成・編集・LoRA 学習を MLX 上で実行。 |

## Models

| Model | License | Terms | Size | Description |
|---|---|---|---:|---|
| [black-forest-labs/FLUX.2-klein-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) | FLUX Non-Commercial License | 要 | 52.9 GB | `klein-9b`（デフォルト）。少ステップ向けの 9B Klein。既定は `steps: 4`、`guidance: 1.0`、`quantize: null`。生成・編集に使える。 |
| [black-forest-labs/FLUX.2-klein-base-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B) | Apache-2.0 | 不要 | 23.7 GB | `klein-base-4b`。base variant。既定は `steps: 40`、`guidance: 1.0`、`quantize: 8`。生成・編集・LoRA 学習に使える。 |
| [black-forest-labs/FLUX.2-klein-base-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) | FLUX Non-Commercial License | 要 | 52.9 GB | `klein-base-9b`。base variant。既定は `steps: 40`、`guidance: 1.0`、`quantize: 8`。生成・編集・LoRA 学習に使える。 |

## Notes

- **サイズ制約**:
  `width` / `height` は 16 の倍数。既定は `1024 x 1024`、上限は `2048 x 2048`。
  `steps` の上限は `100`。
- **LoRA 適用**:
  `loras: [{"file": {"type": "file_id", "file_id": "..."}, "scale": 1.0}]` で学習済みアダプタを適用する。
  最大 4 つまで。`scale` は効きの強さ。
- **LoRA 学習データセット**:
  ZIP は画像をトップレベル、または単一サブフォルダに入れる。
  `training_mode: "text"` では各画像に同じ語幹の `.txt` キャプションが必要。
  `training_mode: "edit"` では `*_in.*` / `*_out.*` の画像ペアと `*_in.txt` プロンプトが必要。
- **メモリ目安**:
  `klein-9b` は約 29 GiB、edit では約 31.6 GiB のピーク実測。
  `klein-base-4b` は q8 / 512 / 40 steps で約 9.1 GiB、
  `klein-base-9b` は約 16.8 GiB。train は `KIAPI_FLUX2_TRAIN_RESERVE_GB`
  既定 24 GiB を予約する。

## Quickstart

### generate — txt2img

```bash
jq -n \
'{
  model: "klein-9b",
  mode: "sync",
  prompt: "a cafe storefront, a sign clearly reads CAFE, bright daylight",
  width: 512,
  height: 512,
  seed: 1
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/generate \
-H 'Content-Type: application/json' \
--data-binary @- \
-o flux2.png
```

Job JSON が欲しい場合:

```bash
jq -n \
'{
  model: "klein-9b",
  mode: "sync",
  prompt: "a small robot watering flowers, clean studio illustration",
  width: 512,
  height: 512,
  seed: 2
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary @- |
jq .
```

### generate — img2img

先にソース画像をアップロードする:

```bash
IMG=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@source.png" | jq -r .file_id)
```

```bash
jq -n \
--arg img "$IMG" \
'{
  model: "klein-9b",
  mode: "sync",
  prompt: "turn this into a polished cozy illustration",
  init_image: {type: "file_id", file_id: $img},
  image_strength: 0.45,
  width: 1024,
  height: 576,
  seed: 7
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/generate \
-H 'Content-Type: application/json' \
--data-binary @- \
-o flux2-img2img.png
```

`image_strength` は 0-1。小さいほど入力画像を強く残し、大きいほどプロンプト側に寄る。

### edit — 複数参照画像での編集

```bash
REF1=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@mascot.png" | jq -r .file_id)
REF2=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@object.png" | jq -r .file_id)

jq -n \
--arg ref1 "$REF1" \
--arg ref2 "$REF2" \
'{
  model: "klein-9b",
  mode: "sync",
  prompt: "make a playful illustration combining the mascot and object",
  images: [{type: "file_id", file_id: $ref1}, {type: "file_id", file_id: $ref2}],
  width: 1024,
  height: 576,
  seed: 9
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/edit \
-H 'Content-Type: application/json' \
--data-binary @- \
-o flux2-edit.png
```

### async

```bash
JOB=$(
jq -n \
'{
  model: "klein-9b",
  mode: "async",
  prompt: "a cinematic product photo of a glass teapot",
  width: 512,
  height: 512,
  seed: 11
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary @- |
jq -r .job_id
)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```

完了後、Job の `artifacts[0]` または `result.file_id` を使って画像を取得する:

```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o flux2-async.png
```

### train — LoRA

`training_mode: "text"` のデータセット例:

```text
my_lora/
  sample_01.png
  sample_01.txt
  sample_02.png
  sample_02.txt
```

データセット ZIP を作り、Files API にアップロードする:

```bash
(cd my_lora && zip -q -r - .) > dataset.zip

DS=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@dataset.zip" | jq -r .file_id)
```

学習を開始する。train は常に async:

```bash
JOB=$(
jq -n \
--arg ds "$DS" \
'{
  model: "klein-base-4b",
  dataset: {type: "file_id", file_id: $ds},
  training_mode: "text",
  num_epochs: 10,
  lora_rank: 8
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/train \
-H 'Content-Type: application/json' \
--data-binary @- |
jq -r .job_id
)

echo "$JOB"
```

完了までポーリングし、学習済みアダプタの `file_id` を取得する:

```bash
until STATUS=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .status) && \
  [ "$STATUS" != "queued" ] && [ "$STATUS" != "running" ]; do
  sleep 5
done

ADAPTER=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.adapter_file_id)
echo "$ADAPTER"
```

### 学習済み LoRA で生成

```bash
jq -n \
--arg adapter "$ADAPTER" \
'{
  model: "klein-base-4b",
  mode: "sync",
  prompt: "<your trigger word> as a clean editorial illustration",
  width: 512,
  height: 512,
  seed: 13,
  loras: [{file: {type: "file_id", file_id: $adapter}, scale: 1.0}]
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/flux2/generate \
-H 'Content-Type: application/json' \
--data-binary @- \
-o flux2-lora.png
```
