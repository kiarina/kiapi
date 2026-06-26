# seedvr2

[English](README.md) | **日本語**

[mflux SeedVR2](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/seedvr2/README.md) で、単一画像の拡散ベース超解像 / アップスケール機能を提供します。
SeedVR2 はプロンプト駆動の画像生成ではなく、入力画像を元にディテールを再構成する image-to-image の超解像モデルです。

- **upscale**:
  - Files API にアップロード済みの画像を `image` FileRef で参照
  - 最短辺の目標ピクセル数、または `"2x"` のような倍率で出力サイズを指定


## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/seedvr2/upscale` | 画像アップスケール | Files API の画像を超解像し、画像を 1 枚生成。 |
| `GET /v1/image/seedvr2/models` | モデル一覧 | 利用可能なモデルの一覧を返す。 |
| `GET /v1/image/seedvr2/openapi.json` | OpenAPI | 詳細な入出力仕様、制約、TIPS を返す。 |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/seedvr2/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/seedvr2/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/seedvr2/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/filipstrand/mflux) | MIT | SeedVR2 の MLX 実装を利用。 |

## Models

| Model | License | Terms | Size | Description |
|---|---|---|---:|---|
| [numz/SeedVR2_comfyUI](https://huggingface.co/numz/SeedVR2_comfyUI) | Apache-2.0 | 不要 | 7.3 GB | `3b`（デフォルト）。軽量 variant。既定は `resolution: "2x"`、`softness: 0.0`、`quantize: 8`。 |
| [numz/SeedVR2_comfyUI](https://huggingface.co/numz/SeedVR2_comfyUI) | Apache-2.0 | 不要 | 17 GB | `7b`。高容量 variant。`3b` より重く、kiapi の登録値では重み約 `7.0 GiB`、実行時ヘッドルーム約 `4.0 GiB` を見込む。 |

モデル重みは `KIAPI_SEEDVR2_MODEL_REPO` で差し替えできます。
既定は `numz/SeedVR2_comfyUI` です。

## Notes

- **resolution**:
  `resolution` は整数の最短辺ターゲット、または `"2x"` / `"1.5x"` のような倍率です。
  整数の場合は既定で `16..2048`、倍率の場合は `> 0` かつ `4.0x` 以下です。
- **softness**:
  `softness` は `0..1`。既定は `0.0` です。入力画像のディテール再構成の柔らかさを調整します。
- **seed**:
  `seed` を省略するとリクエストごとにランダムな seed が割り当てられます。
  再現性が必要な場合は明示してください。
- **quantize override**:
  `quantize` は `3` / `4` / `5` / `6` / `8` / `null`。通常は既定の `8` で常駐モデルを使います。
  リクエストで既定値と異なる `quantize` を指定した場合は、一回限りの一時モデルとしてロード・実行・解放します。
- **レスポンス形式**:
  sync で 1 成果物を生成する場合、`Accept: application/json` を付けなければ生の画像バイト列を返します。
  `X-Kiapi-File-Id` と `X-Kiapi-Job-Id` ヘッダから保存済み成果物と Job を参照できます。
  Job JSON が欲しい場合、または async の場合は `Accept: application/json` を使います。
- **出力形式**:
  `format` は `png`（既定）/ `jpeg` / `webp`。`jpeg` / `webp` では `quality`
  `1..100`（既定 `90`）を使います。
- **メモリ目安**:
  `3b` は重み約 `2.7 GiB`、実行時ヘッドルーム約 `1.5 GiB`、`7b` は重み約
  `7.0 GiB`、実行時ヘッドルーム約 `4.0 GiB` として登録されています。
- **未対応**:
  テキストプロンプト、画像編集指示、LoRA 学習、複数画像入力は公開していません。

## Quickstart

### upscale - 画像をアップロード

先にソース画像を Files API にアップロードします。

```bash
IMG=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@source.png" | jq -r .file_id)
```

### upscale - 倍率で指定

画像だけを保存する:

```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
'{
  model: "3b",
  mode: "sync",
  image: {type: "file_id", file_id: $image},
  resolution: "2x",
  softness: 0.0,
  seed: 42
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/seedvr2/upscale \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o seedvr2-2x.png
```

Job JSON を返す:

```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
'{
  model: "3b",
  mode: "sync",
  image: {type: "file_id", file_id: $image},
  resolution: "2x",
  format: "webp",
  quality: 92,
  seed: 7
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/seedvr2/upscale \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq .
```

### upscale - 最短辺ピクセル数で指定

最短辺を `768px` に合わせてアップスケールします。

```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
'{
  mode: "sync",
  image: {type: "file_id", file_id: $image},
  resolution: 768,
  softness: 0.15,
  seed: 11
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/seedvr2/upscale \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o seedvr2-768.png
```

`resolution` に `"768"` のような文字列を渡した場合も整数ターゲットとして解釈されます。

### 7b variant

```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
'{
  model: "7b",
  mode: "sync",
  image: {type: "file_id", file_id: $image},
  resolution: "2x",
  seed: 13
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/seedvr2/upscale \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o seedvr2-7b.png
```

### async

```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
'{
  mode: "async",
  image: {type: "file_id", file_id: $image},
  resolution: "2x",
  seed: 17
}'
)

JOB=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/seedvr2/upscale \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq -r .job_id)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```

完了後、Job の `artifacts[0]` または `result.file_id` を使って画像を取得します。

```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o seedvr2-async.png
```

### quantize override

既定と異なる量子化で試す場合は `quantize` を明示します。この呼び出しは常駐モデルを
再利用せず、一時モデルを構築します。

```bash
PARAMS=$(
jq -n \
--arg image "$IMG" \
'{
  model: "3b",
  mode: "sync",
  image: {type: "file_id", file_id: $image},
  resolution: "1.5x",
  quantize: 6,
  seed: 19
}'
)

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/seedvr2/upscale \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o seedvr2-q6.png
```

### モデル一覧とヘルプ

```bash
curl -sS http://localhost:${PORT:-8000}/v1/image/seedvr2/models | jq .
curl -sS http://localhost:${PORT:-8000}/v1/image/seedvr2/openapi.json | jq .
```
