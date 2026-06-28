# audiogen

[English](README.md) | **日本語**

[AudioGen](https://huggingface.co/facebook/audiogen-medium) で、効果音生成機能を提供します。

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/audio/audiogen/generate` | 効果音生成 | プロンプトから効果音を生成。**16 kHz モノラル WAV 最大10秒**。 |
| `GET /v1/audio/audiogen/models` | モデル一覧 | 利用可能なモデルの一覧を返す。 |
| `GET /v1/audio/audiogen/openapi.json` | OpenAPI | 詳細な入出力仕様、使い方、TIPS を返す。 |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/audio/audiogen/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/audio/audiogen/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/audio/audiogen/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mlx-audiocraft](https://github.com/theashishmaurya/mlx-audiocraft) | MIT | Meta AudioCraft の AudioGen を MLX へ移植。 |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [facebook/audiogen-medium](https://huggingface.co/facebook/audiogen-medium) | CC-BY-NC-4.0 | 不要 | 3.6 GB | ~9 GB | **非商用ライセンス**。16 kHz モノラル、約 0.5 倍速（5 秒のクリップで約 10 秒の計算）。 |

## Quickstart

### generate — 効果音生成

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
