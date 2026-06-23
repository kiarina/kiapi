# qwen

[English](README.md) | **日本語**

[mflux Qwen Image](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/qwen/README.md) で、画像生成・画像編集機能を提供します。
Qwen Image は多言語プロンプトと画像内テキストに強いモデルです。

- **generate**:
  - テキストから画像を生成
  - `init_image` FileRef を渡した場合は img2img
- **edit**:
  - Files API の 1 枚以上の参照画像を使う自然言語編集


## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/qwen/generate` | 画像生成 | プロンプトと参照画像から画像を生成。 |
| `POST /v1/image/qwen/edit` | 画像編集 | 複数の参照画像から画像を生成。 |
| `GET /v1/image/qwen/models` | モデル一覧 | 利用可能なモデルの一覧を返す。 |
| `GET /v1/image/qwen/openapi.json` | OpenAPI | 詳細な入出力仕様、使い方、TIPS を返す。 |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/qwen/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/qwen/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/qwen/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/filipstrand/mflux) | MIT | Qwen Image / Qwen Image Edit を MLX 上で実行。 |

## Models

| Model | License | Terms | Size | Description |
|---|---|---|---:|---|
| [Qwen/Qwen-Image](https://huggingface.co/Qwen/Qwen-Image) | Apache-2.0 | 不要 | 58 GB | `image`（デフォルト）。`generate` で使用。txt2img / img2img。既定は `steps: 30`、`guidance: 4.0`、`quantize: 8`。 |
| [Qwen/Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509) | Apache-2.0 | 不要 | 58 GB | `edit-2509`。`edit` で使用。単一/複数参照画像の編集。既定は `steps: 30`、`guidance: 2.5`、`quantize: 8`。 |

`POST /v1/image/qwen/generate` は `image` のみ、`POST /v1/image/qwen/edit` は
`edit-2509` のみを受け付けます。エンドポイントごとのデフォルトは router 側で補われる
ため、通常は `model` を省略できます。

## Notes

- **画像サイズ**:
  `width` / `height` は 16 の倍数。既定は `1024 x 1024`、上限は `2048 x 2048`。
- **steps / guidance**:
  `steps` は `1..100`。省略時は generate/edit とも `30`。`guidance` は generate が
  `4.0`、edit が `2.5`。
- **quantize**:
  既定は `8`。上書きする場合は `3` / `4` / `5` / `6` / `8` を指定できます。
  省略、または `null` を渡すと既定値を使います。
- **LoRA 適用**:
  `loras: [{"file": {"type": "file_id", "file_id": "..."}, "scale": 1.0}]` でアダプタを適用します。最大 4 つまで。
  アダプタファイルは Files API に保存されている必要があります。
- **transient モデル**:
  mflux は量子化レベルと LoRA をモデル構築時に固定するため、`loras` を持つ、または
  `quantize` を既定値から上書きするリクエストは、その呼び出し用の一時モデルを構築します。
  常駐モデルを再利用しないため、素の `image` / `edit-2509` 呼び出しより遅くなります。
- **出力形式**:
  `format` は `png`（既定）/ `jpeg` / `webp`。`jpeg` / `webp` では `quality`
  `1..100`（既定 `90`）を使います。
- **メモリ目安**:
  `image` / `edit-2509` はどちらも大きなモデルです。kiapi の登録値では重み約
  `22.0 GiB`、実行時ヘッドルーム約 `8.0 GiB` を見込んでいます。

## Quickstart

### generate - テキストから画像生成

画像だけを保存する:

```bash
PARAMS=$(
jq -n \
--arg prompt "a cafe storefront, a wooden sign clearly reads カフェ, bright daylight" \
--arg negative_prompt "blurry, low quality, distorted text" \
'{
  model: "image",
  mode: "sync",
  prompt: $prompt,
  negative_prompt: $negative_prompt,
  width: 512,
  height: 512,
  seed: 1
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o qwen.png
```

Job JSON を返す:

```bash
PARAMS=$(
jq -n \
--arg prompt "a clean product label design, the main text reads KIAPI, white background" \
'{
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 2
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq .
```

### generate - img2img

先にソース画像をアップロードします。

```bash
IMG=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@source.png" | jq -r .file_id)
```

アップロードした画像を元に生成します。

```bash
PARAMS=$(
jq -n \
--arg img "$IMG" \
--arg prompt "turn this into a polished cozy illustration" \
'{
  model: "image",
  mode: "sync",
  prompt: $prompt,
  init_image: {type: "file_id", file_id: $img},
  image_strength: 0.45,
  width: 1024,
  height: 576,
  seed: 7
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o qwen-img2img.png
```

`image_strength` は `0..1`。小さいほど入力画像を強く残し、大きいほどプロンプト側の
変化が強くなります。

### edit - 単一/複数画像の編集

```bash
REF1=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@mascot.png" | jq -r .file_id)
REF2=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@object.png" | jq -r .file_id)

PARAMS=$(
jq -n \
--arg ref1 "$REF1" \
--arg ref2 "$REF2" \
--arg prompt "combine the mascot and object into a bright product key visual; keep the mascot recognizable" \
'{
  model: "edit-2509",
  mode: "sync",
  prompt: $prompt,
  images: [{type: "file_id", file_id: $ref1}, {type: "file_id", file_id: $ref2}],
  width: 1024,
  height: 576,
  seed: 9
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/edit \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o qwen-edit.png
```

`images` は 1 枚以上。単一画像の編集にも、複数参照画像を使った合成・再構成にも
使えます。

### async

```bash
PARAMS=$(
jq -n \
--arg prompt "a typography poster, large readable text says LOCAL AI" \
'{
  mode: "async",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 11
}'
)

JOB=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq -r .job_id)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```

完了後、Job の `artifacts[0]` または `result.file_id` を使って画像を取得します。

```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o qwen-async.png
```

### LoRA を適用して生成

学習済みアダプタなどの `.safetensors` を Files API にアップロードし、`loras` で参照します。

```bash
ADAPTER=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@adapter.safetensors" | jq -r .file_id)

PARAMS=$(
jq -n \
--arg adapter "$ADAPTER" \
--arg prompt "<your trigger word> as a clean editorial illustration" \
'{
  model: "image",
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 13,
  loras: [{file: {type: "file_id", file_id: $adapter}, scale: 1.0}]
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/qwen/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o qwen-lora.png
```

`scale` は効きの強さです。`loras` を使うリクエストは毎回一時モデルを構築します。
