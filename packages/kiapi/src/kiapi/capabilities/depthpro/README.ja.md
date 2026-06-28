# depthpro

[English](README.md) | **日本語**

[mflux Depth Pro](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/depth_pro/README.md) で、単一画像から深度マップを推定し、下記を生成します。

- グレースケール PNG の深度マップ
- 任意で、生の深度配列と min/max を含む圧縮 NPZ

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/depthpro/estimate` | 深度推定 | Files API の画像から深度マップを推定。 |
| `GET /v1/image/depthpro/models` | モデル一覧 | 利用可能なモデルの一覧を返す。 |
| `GET /v1/image/depthpro/openapi.json` | OpenAPI | 詳細な入出力仕様、使い方、TIPS を返す。 |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/depthpro/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/depthpro/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/depthpro/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/filipstrand/mflux) | MIT | Depth Pro の MLX 実装を利用。 |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [apple/DepthPro](https://huggingface.co/apple/DepthPro) | Apple Depth Pro License | 不要 | 1.8 GB | ~4 GB | `base`（デフォルト）。単一画像から相対深度を推定。既定は `quantize: 8`。初回利用時にモデルをダウンロードすることがある。 |

## Notes

- **レスポンス形式**:
  `include_depth_data: true`（デフォルト）では PNG と NPZ の 2 成果物を作るため、
  sync でも Job JSON を返す。`include_depth_data: false` では PNG のみになり、
  sync はデフォルトで生の PNG バイト列を返す。Job JSON が必要な場合は
  `Accept: application/json` を付ける。
- **quantize override**:
  `quantize` は `3` / `4` / `5` / `6` / `8` / `null`。通常は常駐モデルを使うが、
  リクエストで既定値と異なる `quantize` を指定した場合は、一回限りの一時モデルとして
  ロード・実行・解放する。
- **入力サイズ上限**:
  既定では入力画像は `4096 * 4096` pixels まで。Depth Pro は内部でリサイズするが、
  大きすぎる入力でキューを長時間占有しないように制限している。
- **進捗**:
  Depth Pro は単一 forward pass で細かいステップ通知を持たないため、実行中は時間ベースの
  synthetic progress を流す。

## Quickstart

### estimate — 深度推定

先にソース画像をアップロードする:

```bash
IMG=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@source.png" | jq -r .file_id)
```

深度 PNG と生データ NPZ の両方を作る:

```bash
PARAMS=$(jq -n \
--arg img "$IMG" \
'{
  model: "base",
  mode: "sync",
  image: {type: "file_id", file_id: $img},
  quantize: 8,
  include_depth_data: true
}')

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/depthpro/estimate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" | jq .
```

表示用の深度 PNG だけが欲しい場合:

```bash
PARAMS=$(jq -n \
--arg img "$IMG" \
'{
  model: "base",
  mode: "sync",
  image: {type: "file_id", file_id: $img},
  include_depth_data: false
}')

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/depthpro/estimate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o depth.png
```

### async

```bash
PARAMS=$(jq -n \
--arg img "$IMG" \
'{
  model: "base",
  mode: "async",
  image: {type: "file_id", file_id: $img},
  include_depth_data: true
}')

JOB=$(
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/depthpro/estimate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq -r .job_id
)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```

完了後、Job の `artifacts` または `result.depth_image_file_id` /
`result.depth_data_file_id` を使って成果物を取得できます。

```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.depth_image_file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o depth.png
```
