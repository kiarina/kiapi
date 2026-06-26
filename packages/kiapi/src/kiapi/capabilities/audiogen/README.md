# audiogen

**English** | [日本語](README.ja.md)

[AudioGen](https://huggingface.co/facebook/audiogen-medium) provides sound effect generation functionality.

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/audio/audiogen/generate` | Sound effect generation | Generate sound effects from prompts. **16 kHz monaural WAV up to 10 seconds**. |
| `GET /v1/audio/audiogen/models` | Model list | Returns a list of available models. |
| `GET /v1/audio/audiogen/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/audio/audiogen/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/audio/audiogen/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/audio/audiogen/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mlx-audiocraft](https://github.com/theashishmaurya/mlx-audiocraft) | MIT | Porting Meta AudioCraft's AudioGen to MLX. |

## Models

| Model | License | Terms | Size | Description |
|---|---|---|---:|---|
| [facebook/audiogen-medium](https://huggingface.co/facebook/audiogen-medium) | CC-BY-NC-4.0 | Not required | 3.6 GB | **Non-Commercial License**. 16 kHz monaural, approximately 0.5x speed (approximately 10 seconds calculation for a 5 second clip). |

## Quickstart

### generate — sound effect generation
```bash
jq -n \
--arg prompt "heavy rain on a tin roof, distant thunder" \
'{
  mode: "sync",
  prompt: $prompt,
  duration: 5
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/audio/audiogen/generate \
-H 'Content-Type: application/json' \
--data-binary @- \
-o sfx.wav
```
