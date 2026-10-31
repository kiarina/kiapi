# embedding

[mlx-embeddings](https://github.com/Blaizzy/mlx-embeddings) provides a text/image embedding API.

`POST /v1/embeddings` follows OpenAI's embeddings API.

- **text embedding**:
  - Qwen3-Embedding-8B
- **multimodal embedding**:
  - Qwen3-VL-Embedding-2B

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/embeddings` | Embeddings | OpenAI-compatible. Returns `{ object, data, model, usage, timings }`. |
| `GET /v1/embedding/models` | Model list | Returns a list of available models. |
| `GET /v1/embedding/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

`GET /v1/models` lists chat models only.

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
- In the VL model, an object with both `text` and `image` is embedded as one combined item.

## Notes

- **Request**:
  `input` takes a string, an array of up to 2048 items, or a `{text, image}` object.
  Objects are a kiapi extension for multimodal models. Token arrays are not accepted.
  `dimensions` and `encoding_format` follow OpenAI.
- **Response**:
  `data` holds one `{ object, index, embedding }` per input.
  `usage` counts text tokens; images are not counted.
  `timings` is a kiapi extension.
- **Output Vector**:
  Convert the output of `mlx-embeddings` to a Python `list[float]` with `_utils/to_vector.py`.
  In the help, it is treated as a vector for L2 normalization and last-token pooling.
  `dimensions` truncates the vector and normalizes it again:
  32-4096 for `qwen3-embedding-8b`, 64-2048 for `qwen3-vl-embedding-2b`.
- **Input format**:
  `text` passes the string as is. Empty text is rejected.
  `image` accepts base64, data URLs, http(s) URLs,
  Materialize to a temporary file before running the VL model.
- **max_length**:
  Text longer than `KIAPI_EMBEDDING_MAX_LENGTH` tokens returns HTTP 400 instead of being truncated.
  Default value is `32768`, the sequence length of both models.
  `mlx_embeddings.generate` ignores `max_length` for a string, so the handlers check the length.
- **Instructions**:
  Text is embedded as sent. Upstream recommends prefixing queries with
  `Instruct: {task}\nQuery:{query}`; callers add it when they want it.
- **Two embedded paths**:
  The text model is `mlx_embeddings.generate(...)`,
  VL models use `model.process([item], processor=...)`.
  The paths are different even within the same dependent library, so please verify both when updating `mlx-embeddings`.
- **Items run one at a time**:
  A padded batch would cost the longest item's length for every item.
- **Speed**:
  On a Mac Studio M4 Max, `qwen3-embedding-8b` takes about
  `0.00135 * tokens + 0.000000094 * tokens^2` seconds per input, so long inputs slow down
  faster than their length: about 1.4 s per 1k tokens up to 2k tokens, 2.0 s at 8k, and 4.3 s at 32k.
  Splitting 31.6k tokens into 8 items takes 49 s instead of 136 s; below 2k tokens per item
  it stops getting faster.
  Requests share one worker, so a long input also delays other generation.
  `scripts/capabilities/measure_embedding_speed.py` repeats the measurement.
- **VL processor correction**:
  MLX converted Qwen3-VL processors may lack `chat_template` and image/video token-id attributes.
  `_patch_processor` in `_models/qwen3_vl.py` compensates with best-effort.
  When updating dependencies, please check whether this correction is still required.

## Quickstart

### text - default model
```bash
jq -n \
'{
  input: "今日はいい天気ですね"
}' |
curl -sS http://localhost:${PORT:-8000}/v1/embeddings \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '{model, usage, dimension: (.data[0].embedding | length), head: .data[0].embedding[0:5], timings}'
```
### OpenAI SDK
```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="unused")
response = client.embeddings.create(
    model="qwen3-embedding-8b",
    input=["今日はいい天気ですね", "明日は雨です"],
    dimensions=1024,
)
vectors = [item.embedding for item in response.data]
```
### text - VL model
```bash
jq -n \
'{
  model: "vl",
  input: "a photo of a cat"
}' |
curl -sS http://localhost:${PORT:-8000}/v1/embeddings \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '{model, dimension: (.data[0].embedding | length), timings}'
```
### image - VL model
```bash
IMG=$(base64 -i your_image.png)

jq -n \
--arg image "$IMG" \
'{
  model: "vl",
  input: [{image: $image}]
}' |
curl -sS http://localhost:${PORT:-8000}/v1/embeddings \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '{model, dimension: (.data[0].embedding | length), timings}'
```
### text + image - VL model
```bash
IMG=$(base64 -i your_image.png)

jq -n \
--arg image "$IMG" \
'{
  model: "vl",
  input: [{text: "a photo of a cat", image: $image}]
}' |
curl -sS http://localhost:${PORT:-8000}/v1/embeddings \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '{model, dimension: (.data[0].embedding | length), timings}'
```
### Model list
```bash
curl -sS http://localhost:${PORT:-8000}/v1/embedding/models | jq .
```
