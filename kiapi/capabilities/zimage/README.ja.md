# zimage

[English](README.md) | **日本語**

[mflux Z-Image](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/z_image/README.md) で、画像生成と LoRA ファインチューニング機能を提供します。

Z-Image は比較的軽量に扱える画像生成モデルです。
`turbo` は少ステップで高速、`base` は guidance / negative prompt を使った調整向きです。

- **generate**: テキストから画像を生成
- **train**: キャプション付き画像 ZIP から LoRA アダプタを学習

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/zimage/generate` | 画像生成 | プロンプトから画像を生成。`application/json` の body を渡す。 |
| `POST /v1/image/zimage/train` | LoRA 学習 | キャプション付き画像 ZIP から LoRA アダプタを学習。常に async。 |
| `GET /v1/image/zimage/models` | モデル一覧 | 利用可能なモデルの一覧を返す。 |
| `GET /v1/image/zimage/openapi.json` | OpenAPI | 詳細な入出力仕様、使い方、TIPS を返す。 |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/zimage/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/zimage/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/zimage/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/filipstrand/mflux) | MIT | Z-Image の生成と LoRA 学習を MLX 上で実行。 |

## Models

| Model | License | Terms | Size | Description |
|---|---|---|---:|---|
| [filipstrand/Z-Image-Turbo-mflux-4bit](https://huggingface.co/filipstrand/Z-Image-Turbo-mflux-4bit) | Tongyi Qianwen License | 不要 | 5.5 GB | `turbo`（デフォルト）。蒸留・少ステップ向け。既定は `steps: 9`、`guidance: null`、`quantize: null`。 |
| [Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image) | Apache-2.0 | 不要 | 19 GB | `base`。非 distilled のモデル。既定は `steps: 28`、`guidance: 4.0`、`quantize: 8`。 |

kiapi の登録値では、`turbo` は重み約 `6.0 GiB` / 実行時ヘッドルーム約 `8.0 GiB`、
`base` は重み約 `12.0 GiB` / 実行時ヘッドルーム約 `16.0 GiB` を見込んでいます。

## Notes

- **画像サイズ**:
  `width` / `height` は 16 の倍数。既定は `1024 x 1024`、上限は `2048 x 2048`。
- **steps / guidance**:
  `steps` は `1..100`。省略時は `turbo` が `9`、`base` が `28`。
  `turbo` は distilled model なので `guidance` と `negative_prompt` の効果はありません。
  `base` は `guidance` と `negative_prompt` を使えます。
- **quantize**:
  `quantize` は `3` / `4` / `5` / `6` / `8` を指定できます。省略するとモデルごとの既定値を使います。
  `turbo` は 4-bit 事前量子化 repo を使うため、通常は省略します。
- **LoRA 適用**:
  `generate` の `loras` には `[{ "file": {"type": "file_id", "file_id": "..."}, "scale": 1.0 }]` を渡します。
  既定では最大 4 個まで適用できます。アダプタファイルは Files API に保存されている必要があります。
- **transient モデル**:
  mflux は量子化レベルと LoRA をモデル構築時に固定します。`loras` を持つ、または
  `quantize` を既定値から上書きするリクエストは、その呼び出し用の一時モデルを構築します。
  常駐モデルを再利用しないため、素の `turbo` / `base` 呼び出しより遅くなります。
- **出力形式**:
  `format` は `png`（既定）/ `jpeg` / `webp`。`jpeg` / `webp` では `quality`
  `1..100`（既定 `90`）を使います。
- **LoRA 学習データセット**:
  ZIP のトップレベル、または ZIP 内の単一サブフォルダに画像を置きます。画像ごとに
  同じ語幹の `.txt` キャプションが必要です。

## Quickstart

### generate - テキストから画像生成

画像だけを保存する:

```bash
PARAMS=$(
jq -n \
--arg prompt "a red fox in fresh snow, soft morning light, realistic photo" \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  width: 1024,
  height: 1024,
  seed: 1
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/zimage/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o zimage.png
```

Job JSON を返す:

```bash
PARAMS=$(
jq -n \
--arg prompt "a small robot watering flowers, clean studio illustration" \
--arg negative_prompt "blurry, low quality" \
'{
  model: "base",
  mode: "sync",
  prompt: $prompt,
  negative_prompt: $negative_prompt,
  width: 512,
  height: 512,
  seed: 2
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/zimage/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq .
```

`file_id` が必要な場合はレスポンスヘッダから読めます。

```bash
PARAMS=$(
jq -n \
--arg prompt "a red fox in fresh snow" \
'{
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 1
}'
)

FILE_ID=$(curl -sS -D - -o zimage.png \
-X POST http://localhost:${PORT:-8000}/v1/image/zimage/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
| awk -F': ' 'tolower($1)=="x-kiapi-file-id"{print $2}' | tr -d '\r')

echo "$FILE_ID"
```

### async

```bash
PARAMS=$(
jq -n \
--arg prompt "a cinematic product photo of a glass teapot" \
'{
  model: "turbo",
  mode: "async",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 11
}'
)

JOB=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/zimage/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq -r .job_id)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```

完了後、Job の `artifacts[0]` または `result.file_id` を使って画像を取得します。

```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o zimage-async.png
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

データセット ZIP を作り、Files API にアップロードします。

```bash
(cd dataset && zip -q -r - .) > dataset.zip

DATASET_ID=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@dataset.zip;type=application/zip" | jq -r .file_id)
```

学習を開始します。train は常に async です。

```bash
JOB=$(
jq -n \
--arg dataset "$DATASET_ID" \
'{
  model: "turbo",
  dataset: {type: "file_id", file_id: $dataset},
  num_epochs: 10,
  lora_rank: 16,
  max_resolution: 512
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/zimage/train \
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

生成で LoRA を適用します。

```bash
PARAMS=$(
jq -n \
--arg prompt "<your trigger word> in a magical garden" \
--arg adapter "$ADAPTER" \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  width: 512,
  height: 512,
  seed: 7,
  loras: [{file: {type: "file_id", file_id: $adapter}, scale: 1.0}]
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/zimage/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o zimage-lora.png
```

`scale` は効きの強さです。`loras` を使うリクエストは毎回一時モデルを構築します。
