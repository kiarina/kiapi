# embedding

**English** | [日本語](README.ja.md)

[mlx-embeddings](https://github.com/Blaizzy/mlx-embeddings) provides a text/image embedding API.

- **text embedding**:
  - Qwen3-Embedding-8B
- **multimodal embedding**:
  - Qwen3-VL-Embedding-2B

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/embedding` | Embed | 1 Vectorize item. The response is `{ model, embedding, dimension, usage, timings }`. |
| `GET /v1/embedding/models` | Model list | Returns a list of available models. |
| `GET /v1/embedding/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/embedding/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/embedding/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/embedding/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mlx-embeddings](https://github.com/Blaizzy/mlx-embeddings) | MIT | Drive Qwen3 / Qwen3-VL embedding models on MLX. |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [mlx-community/Qwen3-Embedding-8B-mxfp8](https://huggingface.co/mlx-community/Qwen3-Embedding-8B-mxfp8) | Apache-2.0 | Not required | 7.82 GB | ~9 GB | `qwen3-embedding-8b` (default). text only, 4096 dimensions. alias: `text`, `qwen3-embedding`, `qwen3_embedding`. |
| [mlx-community/Qwen3-VL-Embedding-2B-mxfp8](https://huggingface.co/mlx-community/Qwen3-VL-Embedding-2B-mxfp8) | Apache-2.0 | Not required | 2.59 GB | ~4 GB | `qwen3-vl-embedding-2b`. text + image, 2048 dimensions. alias: `vl`, `qwen3-vl-embedding`, `qwen3_vl_embedding`. |

- **HTTP 400** when sending a modality that is not supported by the selected model.
  Example: Error when sending `image` to `qwen3-embedding-8b`.
- In the VL model, if you send `text` and `image` at the same time, they will be sent as one combined item.
  Embed.

## Notes

- **Response format**:
  `embedding` is a float array and `dimension` is its length.
  `usage` returns `prompt_tokens` / `total_tokens`.
  Currently, the number of tokens remains `0` depending on the model execution path.
- **Output Vector**:
  Convert the output of `mlx-embeddings` to a Python `list[float]` with `_utils/to_vector.py`.
  In the help, it is treated as a vector for L2 normalization and last-token pooling.
- **Input format**:
  `text` passes the string as is.
  `image` accepts base64, data URLs, http(s) URLs,
  Materialize to a temporary file before running the VL model.
- **max_length**:
  The maximum length passed to the tokenizer is set with `KIAPI_EMBEDDING_MAX_LENGTH`.
  Default value is `512`.
- **Two embedded paths**:
  The text model is `mlx_embeddings.generate(...)`,
  VL models use `model.process([item], processor=...)`.
  The paths are different even within the same dependent library, so please verify both when updating `mlx-embeddings`.
- **VL processor correction**:
  MLX converted Qwen3-VL processors may lack `chat_template` and image/video token-id attributes.
  `_patch_processor` in `_models/qwen3_vl.py` compensates with best-effort.
  When updating dependencies, please check whether this correction is still required.

## Quickstart

### text - default model
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
### text - VL model
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
### image - VL model
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
### text + image - VL model
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
### Model list
```bash
curl -sS http://localhost:${PORT:-8000}/v1/embedding/models | jq .
```
