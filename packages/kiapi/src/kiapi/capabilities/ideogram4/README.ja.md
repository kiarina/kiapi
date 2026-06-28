# ideogram4

[English](README.md) | **日本語**

[mflux Ideogram 4 FP8](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/ideogram4/README.md) で、タイポグラフィに強いテキスト画像生成機能を提供します。
Ideogram 4 は、画像内の文字・看板・ラベル・ロゴ風テキストなどを扱いたい場面に向いたモデルです。
kiapi では txt2img のみを公開し、生成結果を Files API の成果物として保存します。

- **generate**:
  - Ideogram 4 の JSON caption、または通常のテキストプロンプトから画像を生成


## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/ideogram4/generate` | 画像生成 | JSON caption またはテキストプロンプトから画像を 1 枚生成。 |
| `GET /v1/image/ideogram4/models` | モデル一覧 | 利用可能なモデルの一覧を返す。 |
| `GET /v1/image/ideogram4/openapi.json` | OpenAPI | 詳細な入出力仕様、プロンプト形状、制約、TIPS を返す。 |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/ideogram4/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/ideogram4/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/ideogram4/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/filipstrand/mflux) | MIT | Ideogram 4 FP8 の MLX 実装を利用。 |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [ideogram-ai/ideogram-4-fp8](https://huggingface.co/ideogram-ai/ideogram-4-fp8) | Ideogram license (非商用) | 必要 | 27.5 GB | ~30 GB | `fp8`（デフォルト）。Hugging Face の gated repo。既定は `1024x1024`、`preset: V4_DEFAULT_20`、`quantize: null`。 |

## Notes

- **Hugging Face の gated repo**:
  モデル重みは `ideogram-ai/ideogram-4-fp8` から取得します。
  初回実行前に Hugging Face 上でアクセス承認を済ませ、ローカル環境で認証しておく必要があります。
- **JSON caption 推奨**:
  通常の文字列プロンプトも受け付けますが、Ideogram 4 は構造化された JSON caption で最も性能を発揮します。
  画像内テキストを狙う場合は、`compositional_deconstruction.elements[]` に `type: "text"`、
  `bbox`、`text`、`desc` を入れるのが基本です。
- **bbox 座標**:
  JSON caption の `bbox` は `[x1, y1, x2, y2]` 形式です。
  Ideogram 4 の prompting guide では 0-1000 の正規化レイアウト座標として扱います。
- **プリセット**:
  `preset` は `V4_DEFAULT_20` / `V4_QUALITY_48` / `V4_TURBO_12` のいずれかです。
  既定は `V4_DEFAULT_20`。品質優先なら `V4_QUALITY_48`、速度優先なら `V4_TURBO_12` を使います。
- **画像サイズ**:
  `width` / `height` は 16 の倍数で、既定は `1024x1024`。
  既定の上限は `2048x2048`、下限は `256x256` です。
- **quantize override**:
  `quantize` は `3` / `4` / `5` / `6` / `8` / `null`。
  リクエストで既定値と異なる `quantize` を指定した場合は、一回限りの一時モデルとしてロード・実行・解放します。
- **レスポンス形式**:
  sync で 1 成果物を生成する場合、`Accept: application/json` を付けなければ生の画像バイト列を返します。
  `X-Kiapi-File-Id` と `X-Kiapi-Job-Id` ヘッダから保存済み成果物と Job を参照できます。
  Job JSON が欲しい場合、または async の場合は `Accept: application/json` を使います。
- **出力フォーマット**:
  `format` は `png` / `jpeg` / `webp`。既定は `png`。
  `quality` は `jpeg` / `webp` のエンコード品質で、`1..100`、既定は `90` です。
- **セーフティフィルタ**:
  プロンプトによっては、誤検出を含めて `Image blocked by safety filter` 画像が返ることがあります。
  kiapi はこれを HTTP エラーにはせず、返された画像をそのままアーティファクトとして保存します。
- **未対応**:
  image-to-image、画像編集、LoRA 学習、hosted Magic Prompt API、FP8 以外の checkpoint layout は公開していません。

## Prompt JSON

推奨される JSON caption の基本形です。

```json
{
  "high_level_description": "Overall scene description.",
  "style_description": "Optional style, lighting, medium, and color guidance.",
  "compositional_deconstruction": {
    "background": "Background and layout description.",
    "elements": [
      {
        "type": "text",
        "bbox": [360, 420, 640, 560],
        "text": "HELLO",
        "desc": "Crisp black uppercase letters centered on the sign."
      }
    ]
  }
}
```

詳しい書き方は [Ideogram 4 prompting guide](https://github.com/ideogram-oss/ideogram4/blob/main/docs/prompting.md) も参照してください。

## Quickstart

### generate - JSON caption で文字入り画像を生成

Job JSON を返す:

```bash
PARAMS=$(jq -n '{
  model: "fp8",
  mode: "sync",
  prompt: {
    high_level_description: "A clean studio photo of a white notebook with the word MFLUX on the cover.",
    style_description: "Minimal product photography, soft window light, realistic paper texture.",
    compositional_deconstruction: {
      background: "Warm wooden desk with soft shadows.",
      elements: [
        {
          type: "text",
          bbox: [390, 430, 610, 560],
          text: "MFLUX",
          desc: "Crisp black uppercase letters centered on the notebook cover."
        }
      ]
    }
  },
  width: 1024,
  height: 1024,
  preset: "V4_DEFAULT_20",
  seed: 42
}')

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ideogram4/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq .
```

画像だけを保存する:

```bash
PARAMS=$(jq -n '{
  model: "fp8",
  mode: "sync",
  prompt: {
    high_level_description: "A square cafe poster with the large word KIASA.",
    style_description: "Clean editorial poster, warm morning colors, sharp typography.",
    compositional_deconstruction: {
      background: "Cream wall with a simple coffee cup illustration.",
      elements: [
        {
          type: "text",
          bbox: [260, 320, 740, 500],
          text: "KIASA",
          desc: "Large bold serif letters, perfectly readable."
        }
      ]
    }
  },
  width: 1024,
  height: 1024,
  seed: 7
}')

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ideogram4/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ideogram4.png
```

### generate - プレーンテキスト

```bash
PARAMS=$(jq -n '{
  mode: "sync",
  prompt: "A vintage travel poster for TOKYO, the word TOKYO is large and perfectly readable, bright flat colors",
  width: 768,
  height: 1024,
  preset: "V4_QUALITY_48",
  seed: 11
}')

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ideogram4/generate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o ideogram4-text.png
```

### async

```bash
PARAMS=$(jq -n '{
  mode: "async",
  prompt: {
    high_level_description: "A clean packaging mockup for a tea box labeled HIKARI.",
    compositional_deconstruction: {
      background: "Soft green studio backdrop.",
      elements: [
        {
          type: "text",
          bbox: [330, 360, 670, 520],
          text: "HIKARI",
          desc: "Elegant uppercase letters printed on the front of the box."
        }
      ]
    }
  },
  width: 1024,
  height: 1024,
  preset: "V4_TURBO_12"
}')

JOB=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/ideogram4/generate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq -r .job_id)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```

完了後、Job の `artifacts[0]` または `result.file_id` を使って画像を取得します。

```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o ideogram4-async.png
```

### モデル一覧とヘルプ

```bash
curl -sS http://localhost:${PORT:-8000}/v1/image/ideogram4/models | jq .
curl -sS http://localhost:${PORT:-8000}/v1/image/ideogram4/openapi.json | jq .
```
