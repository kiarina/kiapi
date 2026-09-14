DESCRIPTION = """Text and multimodal embeddings for retrieval and similarity search.

POST one item to `/v1/embedding` with one field per modality (`text` and/or
`image`). Returns a single L2-normalized, last-token-pooled vector. This is **not**
OpenAI's array `input` shape — one item per request. Sync only (no async mode).

## Upstream docs
- [mlx-embeddings](https://github.com/Blaizzy/mlx-embeddings) — the MLX embedding engine kiapi runs
- [mlx-community/Qwen3-Embedding-8B-mxfp8](https://huggingface.co/mlx-community/Qwen3-Embedding-8B-mxfp8) — `qwen3-embedding-8b` weights
- [mlx-community/Qwen3-VL-Embedding-2B-mxfp8](https://huggingface.co/mlx-community/Qwen3-VL-Embedding-2B-mxfp8) — `qwen3-vl-embedding-2b` weights

## Choosing A Model
`model` selects a registered embedding model (full catalog and aliases:
`GET /v1/embedding/models`). The served models differ by input modality, so
choose by what you send:
- **qwen3-embedding-8b** (default) — text only. Larger, stronger text retrieval.
- **qwen3-vl-embedding-2b** — text + image. Use it for image embeddings or a
  shared text/image space; sending `image` to the text-only model returns 400.

Vectors from different models live in different spaces and may differ in
dimensionality — embed both your queries and your corpus with the **same** model.

## Notes
- One input item per request. To embed N items, make N requests.
- Provide at least one modality input; an empty request returns 400.
- Vectors are already L2-normalized, so cosine similarity reduces to a dot
  product.

## Examples

### Text (default model)
```sh
curl -sS http://HOST:PORT/v1/embedding \\
  -H 'Content-Type: application/json' \\
  -d '{"text": "今日の天気は晴れです"}'
```

### Image (multimodal model)
```sh
curl -sS http://HOST:PORT/v1/embedding \\
  -H 'Content-Type: application/json' \\
  -d '{
    "model": "qwen3-vl-embedding-2b",
    "image": "data:image/png;base64,iVBORw0..."
  }'
```
"""
