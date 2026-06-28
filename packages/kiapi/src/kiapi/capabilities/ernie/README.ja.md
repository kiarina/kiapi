# ernie

[English](README.md) | **日本語**

[mflux ERNIE-Image](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/ernie_image/README.md) で、画像生成・画像編集・LoRA ファインチューニング機能を提供します。

- **generate**: テキストから画像を生成
- **edit**: Files API の単一画像をプロンプトで編集
- **train**: キャプション付き画像 ZIP から LoRA アダプタを学習

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/ernie/generate` | 画像生成 | プロンプトから画像を生成。 |
| `POST /v1/image/ernie/edit` | 画像編集 | Files API の単一画像をプロンプトで img2img 編集。 |
| `POST /v1/image/ernie/train` | LoRA 学習 | キャプション付き画像 ZIP から LoRA アダプタを学習。常に async。 |
| `GET /v1/image/ernie/models` | モデル一覧 | 利用可能なモデルの一覧を返す。 |
| `GET /v1/image/ernie/openapi.json` | OpenAPI | 詳細な入出力仕様、使い方、TIPS を返す。 |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/ernie/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/ernie/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/ernie/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/filipstrand/mflux) | MIT | ERNIE-Image の MLX 実装と LoRA 学習機能を利用。 |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [baidu/ERNIE-Image-Turbo](https://huggingface.co/baidu/ERNIE-Image-Turbo) | Apache-2.0 | 不要 | 31.6 GB | ~10 GB | `turbo`（デフォルト）。蒸留 8 ステップモデル。既定は `steps: 8`、`guidance: 1.0`、`quantize: 8`。 |
| [baidu/ERNIE-Image](https://huggingface.co/baidu/ERNIE-Image) | Apache-2.0 | 不要 | 31.6 GB | ~20 GB | `base`。非 distilled のモデル。既定は `steps: 50`、`guidance: 4.0`、`quantize: 8`。 |

## Notes

- **画像サイズ**:
  `width` / `height` は 16 の倍数で、既定は `1024x1024`、上限は `2048x2048` です。
- **edit の正方形ガード**:
  `mflux==0.18.0` では ERNIE img2img の一部の非正方形サイズが latent packing で
  失敗することがあります。kiapi はデフォルトで `edit` の `width == height` を要求します。
  無効にするには `KIAPI_ERNIE_EDIT_REQUIRE_SQUARE=0` を設定します。
- **steps / quantize**:
  `steps` は `1..100`。`quantize` は `3` / `4` / `5` / `6` / `8` / `null` を使います。
  `quantize` を省略するとモデルごとの既定値を使います。
- **LoRA 適用**:
  `generate` / `edit` の `loras` には `[{ "file_id": "...", "scale": 1.0 }]` を渡します。
  既定では最大 4 個まで適用できます。
- **LoRA 学習データセット**:
  ZIP のトップレベル、または ZIP 内の単一サブフォルダに画像を置きます。画像ごとに
  同じ語幹の `.txt` キャプションが必要です。`preview*` で始まる画像はキャプション
  必須チェックから除外されます。

## Quickstart

### generate - テキストから画像生成

Job JSON を返す:

```bash
PARAMS=$(
jq -n \
--arg prompt "A quiet Japanese garden after rain, soft morning light, detailed watercolor" \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  width: 1024,
  height: 1024,
  steps: 8,
  seed: 404
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ernie/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" | jq .
```

画像だけを保存する:

```bash
PARAMS=$(
jq -n \
--arg prompt "A barn owl portrait on a mossy branch, natural wildlife photography" \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  steps: 8,
  seed: 404
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ernie/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ernie.png
```

### edit - 単一画像を編集

先に入力画像をアップロードする:

```bash
IMG=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@tests/assets/miineko.png;type=image/png" | jq -r .file_id)
```

アップロードした画像を編集する:

```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
--arg prompt "Turn this image into a soft watercolor illustration" \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  image: {type: "file_id", file_id: $image},
  image_strength: 0.55,
  width: 512,
  height: 512,
  steps: 8,
  seed: 42
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ernie/edit \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ernie_edit.png
```

`image_strength` は `0..1`。小さいほど元画像を強く残し、大きいほどプロンプト側の
変化が強くなります。

### async

```bash
PARAMS=$(
jq -n \
--arg prompt "A small robot reading a book in a cozy library" \
'{
  model: "turbo",
  mode: "async",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 7
}'
)

JOB=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ernie/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" | jq -r .job_id)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```

完了後、Job の `artifacts[0]` または `result.file_id` を使って画像を取得します。

```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o ernie_async.png
```

### train - LoRA ファインチューニング

画像と同じ語幹の `.txt` キャプションを含む ZIP データセットを用意します。

```text
dataset/
  sample_00.png
  sample_00.txt
  sample_01.png
  sample_01.txt
```

データセットをアップロードして学習を開始します。

```bash
DATASET_ID=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@dataset.zip;type=application/zip" | jq -r .file_id)

JOB=$(
jq -n \
--arg dataset "$DATASET_ID" \
'{
  model: "turbo",
  dataset: {type: "file_id", file_id: $dataset},
  num_epochs: 1,
  lora_rank: 16,
  max_resolution: 512
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ernie/train \
-H 'Content-Type: application/json' \
--data-binary @- |
jq -r .job_id
)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```

完了後、`result.adapter_file_id` が学習済みアダプタです。

```bash
ADAPTER=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.adapter_file_id)
```

生成や編集で LoRA を適用します。

```bash
PARAMS=$(
jq -n \
--arg adapter "$ADAPTER" \
--arg prompt "portrait in the trained character style" \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  loras: [{file: {type: "file_id", file_id: $adapter}, scale: 1.0}]
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ernie/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ernie_lora.png
```
