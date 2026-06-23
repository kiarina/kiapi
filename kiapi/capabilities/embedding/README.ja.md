# embedding

[English](README.md) | **日本語**

[mlx-embeddings](https://github.com/Blaizzy/mlx-embeddings) で、テキスト / 画像の埋め込み API を提供します。

- **text embedding**:
  - Qwen3-Embedding-8B
- **multimodal embedding**:
  - Qwen3-VL-Embedding-2B

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/embedding` | 埋め込み | 1 アイテムをベクトル化。レスポンスは `{ model, embedding, dimension, usage, timings }`。 |
| `GET /v1/embedding/models` | モデル一覧 | 利用可能なモデルの一覧を返す。 |
| `GET /v1/embedding/openapi.json` | OpenAPI | 詳細な入出力仕様、使い方、TIPS を返す。 |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/embedding/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/embedding/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/embedding/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mlx-embeddings](https://github.com/Blaizzy/mlx-embeddings) | MIT | Qwen3 / Qwen3-VL 埋め込みモデルを MLX 上で駆動。 |

## Models

| Model | License | Terms | Size | Description |
|---|---|---|---:|---|
| [mlx-community/Qwen3-Embedding-8B-mxfp8](https://huggingface.co/mlx-community/Qwen3-Embedding-8B-mxfp8) | Apache-2.0 | 不要 | 7.82 GB | `qwen3-embedding-8b`（デフォルト）。text 専用、4096 次元。alias: `text`, `qwen3-embedding`, `qwen3_embedding`。 |
| [mlx-community/Qwen3-VL-Embedding-2B-mxfp8](https://huggingface.co/mlx-community/Qwen3-VL-Embedding-2B-mxfp8) | Apache-2.0 | 不要 | 2.59 GB | `qwen3-vl-embedding-2b`。text + image、2048 次元。alias: `vl`, `qwen3-vl-embedding`, `qwen3_vl_embedding`。 |

- 選択したモデルが対応しないモダリティを送ると **HTTP 400**。
  例: `qwen3-embedding-8b` に `image` を送るとエラー。
- VL モデルでは `text` と `image` を同時に送ると、1 つの結合アイテムとして
  埋め込みます。

## Notes

- **レスポンス形式**:
  `embedding` は float 配列、`dimension` はその長さです。
  `usage` は `prompt_tokens` / `total_tokens` を返します。
  現在、モデル実行経路によっては token 数は `0` のままです。
- **出力ベクトル**:
  `mlx-embeddings` の出力を `_utils/to_vector.py` で Python の `list[float]` に変換します。
  ヘルプでは L2 正規化・last-token pooling のベクトルとして扱います。
- **入力形式**:
  `text` は文字列をそのまま渡します。
  `image` は base64、data URL、http(s) URL を受け付け、
  VL モデル実行前に一時ファイルへ materialize します。
- **max_length**:
  tokenizer へ渡す最大長は `KIAPI_EMBEDDING_MAX_LENGTH` で設定します。
  既定値は `512` です。
- **2 つの埋め込み経路**:
  text モデルは `mlx_embeddings.generate(...)`、
  VL モデルは `model.process([item], processor=...)` を使います。
  同じ依存ライブラリ内でも経路が違うため、`mlx-embeddings` を更新したときは両方を検証してください。
- **VL processor の補正**:
  MLX 変換版 Qwen3-VL processor は `chat_template` や image/video token-id 属性を欠くことがあります。
  `_models/qwen3_vl.py` の `_patch_processor` が best-effort で補います。
  依存更新時はこの補正がまだ必要か確認してください。

## Quickstart

### text - デフォルトモデル

```bash
jq -n \
'{
  text: "今日はいい天気ですね"
}' |
curl -sS http://localhost:${PORT:-8000}/v1/embedding \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '{model, dimension, head: .embedding[0:5], timings}'
```

### text - VL モデル

```bash
jq -n \
'{
  model: "vl",
  text: "a photo of a cat"
}' |
curl -sS http://localhost:${PORT:-8000}/v1/embedding \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '{model, dimension, timings}'
```

### image - VL モデル

```bash
IMG=$(base64 -i your_image.png)

jq -n \
--arg image "$IMG" \
'{
  model: "vl",
  image: $image
}' |
curl -sS http://localhost:${PORT:-8000}/v1/embedding \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '{model, dimension, timings}'
```

### text + image - VL モデル

```bash
IMG=$(base64 -i your_image.png)

jq -n \
--arg image "$IMG" \
'{
  model: "vl",
  text: "a photo of a cat",
  image: $image
}' |
curl -sS http://localhost:${PORT:-8000}/v1/embedding \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '{model, dimension, timings}'
```

### モデル一覧

```bash
curl -sS http://localhost:${PORT:-8000}/v1/embedding/models | jq .
```
