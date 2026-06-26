# acestep

[English](README.md) | **日本語**

[ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) で、下記の機能を提供します。
- 音楽生成
- 既存の曲のスタイル変換
- 曲の一部の再生成
- 音源分離

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/audio/acestep/generate` | 音楽生成 | プロンプト, 詩, 時間, 言語を指定して曲を生成。 |
| `POST /v1/audio/acestep/cover` | スタイル変換 | 既存の曲の構成を保ったまま別スタイルに変換。 |
| `POST /v1/audio/acestep/repaint` | 一部再生成 | 曲の時間範囲を再生成。 |
| `POST /v1/audio/acestep/extract` | 音源分離 | 曲のボーカル・ドラムなどの音源を分離。 |
| `GET /v1/audio/acestep/models` | モデル一覧 | 利用可能なモデルの一覧を返す。 |
| `GET /v1/audio/acestep/openapi.json` | OpenAPI | 詳細な入出力仕様、使い方、TIPS を返す。 |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/audio/acestep/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/audio/acestep/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/audio/acestep/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [ace-step](https://github.com/ace-step/ACE-Step-1.5) | MIT | ACE-Step 1.5 本体。 |
| [transformers](https://github.com/huggingface/transformers) | Apache-2.0 | ace-step が要求する 4.x 系。 |
| [PyTorch](https://github.com/pytorch/pytorch) | BSD-3-Clause | ace-step の依存として導入される。 |

## Models

| Model | License | Terms | Size | Description |
|---|---|---|---:|---|
| [ACE-Step/acestep-v15-xl-base](https://huggingface.co/ACE-Step/acestep-v15-xl-base) | MIT | 不要 | 19 GB | `xl-base`（デフォルト）。32ステップ / `guidance_scale=7.0`、最高品質。30秒の音声で約25秒（M4 Max）。 |
| [ACE-Step/Ace-Step1.5](https://huggingface.co/ACE-Step/Ace-Step1.5) | MIT | 不要 | 9.4 GB | `turbo`（8ステップ、`guidance_scale` を無視）の DiT に加え、5Hz LM・VAE・Qwen3-Embedding-0.6B を同梱。速度重視で15秒で約4秒（M4 Max）。 |
| [Qwen/Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | Apache-2.0 | 不要 | 1.1 GB | テキストエンコーダ。ACE-Step/Ace-Step1.5 に同梱。 |

## Notes

- **transformers 4.x の隔離**:
  ACE-Step 1.5 は **transformers 4.x** をピンしており、スタック全体が必要とする **transformers 5.x** と競合する。
  そのため ace-step は専用の **venv** でサブプロセスとして実行する。
  メインプロセスは **`acestep` を import しない**。
- **ローカル配置**:
  `KIAPI_ACESTEP_PYTHON_PATH`, `KIAPI_ACESTEP_PROJECT_ROOT`, `KIAPI_ACESTEP_CHECKPOINT_DIR`
  が未指定の場合、ACE-Step 用の venv / project / checkpoints は
  `core/app` の user data dir 配下の `acestep/` に配置する。
- **IPC**:
  メインプロセスはワーカーと stdin/stdout 上の小さな行指向 JSON プロトコルで通信する。
  各行に `@@KIAPI@@` センチネルを前置。それ以外の stdout はノイズ扱い。
  加えて音声 I/O はファイルパスでやり取りする。
  progress コールバックはジョブの `ProgressReporter` に転送される。

## Quickstart

### generate - 音楽生成

```bash
jq -n \
--arg prompt "Modern J-Pop, 132 BPM, bright piano, emotional electric guitar, upbeat drums" \
--arg lyrics '[Verse 1]
加速する世界の中で
君の声が聴こえてくる

[Chorus]
僕らは光を追いかける
終わらない夢の向こうへ
' \
'{
  model: "turbo",
  mode: "sync",
  prompt: $prompt,
  lyrics: $lyrics,
  duration: 30,
  lang: "ja",
  seed: 1
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/audio/acestep/generate \
-H 'Content-Type: application/json' \
--data-binary @- \
-o song.wav
```

### cover - スタイル変換

```bash
SRC=$(
curl -sS -X POST http://localhost:${PORT:-8000}/v1/files -F "file=@song.wav" |
jq -r .file_id
)

jq -n \
--arg src "$SRC" \
--arg prompt "City Pop, groovy bass, smooth guitar, laid-back 80s production" \
'{
  model: "turbo",
  mode: "sync",
  source: {type: "file_id", file_id: $src},
  prompt: $prompt,
  strength: 0.7,
  seed: 1
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/audio/acestep/cover \
-H 'Content-Type: application/json' \
--data-binary @- \
-o cover.wav
```

`strength`: 0.3 = 緩い再解釈。0.7 = 構成を保ちつつスタイルを変える。1.0 = 厳密。

### repaint - 時間範囲を再生成

```bash
SRC=$(
curl -sS -X POST http://localhost:${PORT:-8000}/v1/files -F "file=@song.wav" |
jq -r .file_id
)

jq -n \
--arg src "$SRC" \
--arg prompt "Dramatic orchestral strings, emotional swell, cinematic" \
'{
  model: "turbo",
  mode: "sync",
  source: {type: "file_id", file_id: $src},
  prompt: $prompt,
  start: 15,
  end: 30,
  strength: 0.6,
  seed: 1
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/audio/acestep/repaint \
-H 'Content-Type: application/json' \
--data-binary @- \
-o repainted.wav
```

`start`/`end` は秒単位（`end: -1` = 最後まで）。

### extract - 音源分離

```bash
SRC=$(
curl -sS -X POST http://localhost:${PORT:-8000}/v1/files -F "file=@song.wav" |
jq -r .file_id
)

RESP=$(
jq -n \
--arg src "$SRC" \
'{
  model: "turbo",
  mode: "sync",
  source: {type: "file_id", file_id: $src},
  targets: ["vocals", "drums", "bass", "other"]
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/audio/acestep/extract \
-H 'Content-Type: application/json' \
-H 'Accept: application/json' \
--data-binary @-
)

# 各音源をダウンロード（stems[] にターゲット名が入る）
echo "$RESP" | jq -c '.result.stems[]' | while read -r s; do
  TARGET=$(echo "$s" | jq -r .target); FID=$(echo "$s" | jq -r .file_id)
  curl -o "${TARGET}.wav" http://localhost:${PORT:-8000}/v1/files/$FID/download
done
```
