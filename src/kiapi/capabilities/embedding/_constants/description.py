DESCRIPTION = """Text and multimodal embeddings for retrieval and similarity search.

`POST /v1/embeddings` follows OpenAI's embeddings API: `input` is a string or an
array, and each input returns one L2-normalized, last-token-pooled vector in
`data`. Multimodal models also accept `{text, image}` objects in `input`, a kiapi
extension. Sync only (no async mode).

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
- `input` accepts up to 2048 items. Items run one at a time.
- Inputs longer than the token limit return 400; they are never truncated.
- Time grows faster than length: about 1.4 s per 1k tokens up to 2k tokens and
  4.3 s per 1k at 32k. Split long documents into items of 2k-4k tokens.
- Empty inputs return 400. Token arrays are not accepted.
- `dimensions` truncates the vector and L2-normalizes it again.
- `usage` counts text tokens; images are not counted.
- Vectors are already L2-normalized, so cosine similarity reduces to a dot
  product.
- `GET /v1/models` lists chat models only. Use `GET /v1/embedding/models` here.

## Examples

### Text (default model)
```sh
curl -sS http://HOST:PORT/v1/embeddings \\
  -H 'Content-Type: application/json' \\
  -d '{"input": "今日の天気は晴れです"}'
```

### Image (multimodal model)
```sh
curl -sS http://HOST:PORT/v1/embeddings \\
  -H 'Content-Type: application/json' \\
  -d '{
    "model": "qwen3-vl-embedding-2b",
    "input": [{"image": "data:image/png;base64,iVBORw0..."}]
  }'
```
"""
