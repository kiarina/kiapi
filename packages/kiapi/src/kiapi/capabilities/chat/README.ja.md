# chat

[English](README.md) | **日本語**

[mlx-vlm](https://github.com/Blaizzy/mlx-vlm) で、OpenAI 互換のチャット補完 API を提供します。

- **vlm** (text + image):
  - Qwen3.6-27B-4bit
- **omni** (text + image + audio + video):
  - Qwen3-Omni-30B-A3B-Instruct-4bit

以下の機能に対応しています。

- streaming
- tool call
- tool choice (auto, any, specific)
- parallel tool calls

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/chat/completions` | チャット補完 | OpenAI 互換の Chat Completions API。 |
| `GET /v1/models` | モデル一覧 | 利用可能なモデルの一覧を返す。 |
| `GET /v1/chat/openapi.json` | OpenAPI | 詳細な入出力仕様、使い方、TIPS を返す。 |

- 独自拡張機能:
  - `fps`: video の変換フレームレート
  - `use_audio_in_video`: video 内音声をモデル入力に含めるか

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/chat/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/chat/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/chat/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mlx-vlm](https://github.com/Blaizzy/mlx-vlm) | MIT | MLX 上で Qwen マルチモーダルモデルを駆動。 |

## Models

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit) | Apache-2.0 | 不要 | 21.8 GB | ~24 GB | `qwen3-omni`（デフォルト）。text + image + audio + video、tool-call prefill=JSON。Talker（音声*出力*）は非公開で出力は text/tool-calls のみ。audio 入力は 1 リクエスト最大 **1 つ**（音声付き video の demux 音声も含む）。 |
| [mlx-community/Qwen3.6-27B-4bit](https://huggingface.co/mlx-community/Qwen3.6-27B-4bit) | Apache-2.0 | 不要 | 16.1 GB | ~19 GB | `qwen3.6-27b`。text + image のみ、tool-call prefill=Hermes/XML。reasoning はデフォルト OFF。 |

- 選択したモデルが対応しないモダリティの part を送ると **HTTP 400**。

## Notes

chat は **mlx-vlm** で実装していますが、バグ回避のためにいくつかパッチを当てています。
このパッチは、**mlx-vlm** のアップデートで壊れる可能性があることを認識してください。

**mlx-vlm** は `mlx-vlm==0.6.3` に固定にしています。
アップデートの際は、下記のパッチの内容を再確認し、必要に応じて修正してください。
詳細は、docstring に記載してあります。

| # | 内容 | 場所 | 対象モデル |
|---|------|------|-----------|
| A | 音声をパスでなく float32 配列で渡す | `_models/qwen3_omni.py` | omni |
| B | ステレオ音声のリサンプル不整合を自前ロードで回避 | `_utils/load_audio_mono.py` | omni |
| C | mlx 0.31.x 用 `mx.where` / `mx.scatter` shim | `_models/qwen3_omni.py` `_ensure_mlx_compat` | omni（image+video 同時） |
| E | ストリーミング detokenizer の UTF-8 デコード緩和 | `_operations/ensure_streaming_detokenizer_compat.py` | 両モデル（stream） |
| F | トークン ID からのテキスト復元（stream） | `_operations/stream_text_from_tokens.py` | qwen3.6（stream） |

**A. 音声を float32 配列で渡す:**
- **場所**: `_models/qwen3_omni.py` の `run`（`audio_arrays = [load_audio_mono(p, sr=sr) ...]`）
- **理由**: mlx-vlm の qwen3-omni 分岐は、生の音声 **パス** を受け取ると
  `could not convert string to float` でクラッシュする。`generate(audio=...)` には
  ndarray を渡す必要がある。
- **トリガ**: omni に音声入力があるすべてのケース。

**B. ステレオ音声のリサンプル不整合:**
- **場所**: `_utils/load_audio_mono.py`（A の配列ロードをこの自前関数で行う）
- **理由**: mlx-vlm の `utils.load_audio` にバグがある。`read_audio` は音声を
  `(samples, channels)`（チャンネルラスト）で返すが、`load_audio` は
  - リサンプルを `resample_audio(..., axis=-1)` ＝ **チャンネル軸**に対して行い、
  - ダウンミックスを `mean(axis=1)` ＝ 同じくチャンネル軸で行う
  と軸の扱いが矛盾している。結果、**レートの異なるステレオ音声**（典型的に
  48kHz / 44.1kHz stereo の wav）は時間軸がリサンプルされず、48kHz のサンプルが
  そのまま 16kHz として omni に渡り、**音声を認識できない**。モノラルは 1 次元で
  `axis=-1` がたまたま時間軸になるため正しく動く。
- **回避策**: `load_audio_mono` では **先にモノラル化してからリサンプル**するため、
  `resample_audio` のデフォルト `axis=-1` が必ず時間軸になり、レート変換が正しく行われる
  （48k mono / 48k stereo / 44.1k stereo / 16k stereo すべて 16000 サンプルへ）。
- **video 内音声への影響**: なし。`_operations/parse_messages.py` の `_extract_audio`
  が ffmpeg `-ac 1 -ar 16000` で **最初からモノラル 16kHz** に demux するため、
  リサンプル・ダウンミックス自体が発生せずバグ条件に該当しない。

**C. mlx 0.31.x 互換 shim（`mx.where` / `mx.scatter`）:**
- **場所**: `_models/qwen3_omni.py` の `_ensure_mlx_compat`（`run` 冒頭で呼ぶ）
- **理由**: mlx-vlm の `qwen3_omni_moe/thinker.py` は **image + video を同時に
  入力する経路**（visual_embeds_multiscale / deepstack 結合）で、mlx 0.31.x に存在
  しない API を使う:
  - 1 引数形式の `mx.where(mask)[0]`（True のインデックス取得）→ TypeError
  - フリー関数 `mx.scatter(a, idx, vals, ax)` → AttributeError

  image 単独・video 単独は別経路で問題なし。site-packages を書き換えず、互換実装を
  グラフトして回避（冪等・加算的で他経路に影響なし）。
- **トリガ**: omni に image と video を **同時に**渡したときのみ。

**E. ストリーミング detokenizer の UTF-8 デコード緩和:**
- **場所**: `_operations/ensure_streaming_detokenizer_compat.py`（stream 経路で呼ぶ）
- **理由**: mlx-vlm の `BPEStreamingDetokenizer.add_token` は、バッファした
  バイト列を **strict UTF-8** でデコードする。フラッシュ境界で不正な UTF-8 になる
  バイトトークン列があるとストリーミング応答がクラッシュする。`finalize` 側は
  同じデコードを寛容に処理しているので、streaming 経路も `errors="replace"` で
  同等に緩和する。
- **トリガ**: 両モデルの `stream=true`。

**F. トークン ID からのテキスト復元（qwen3.6 stream）:**
- **場所**: `_operations/stream_text_from_tokens.py`
- **理由**: バグ回避というより互換ラッパ。mlx-vlm の `_ServerTokenStreamer` /
  `make_streaming_detokenizer` が利用可能なら、それでトークン ID からテキストを
  復元する。利用不可なら素通り（`yield from chunks`）。

## Quickstart

```bash
MODEL=qwen3.6-27b
MODEL=qwen3-omni
```

### text

```sh
jq -n \
--arg model "$MODEL" \
'{
  model: $model,
  messages: [
    {role: "user", content: "こんにちは"}
  ]
}' |
curl -sS "http://localhost:${PORT:-8000}/v1/chat/completions" \
-H 'Content-Type: application/json' \
--data-binary @- |
jq -r '.choices[0].message.content'
# こんにちは！何かお手伝いできることはありますか？
```

ストリーミング:

```sh
jq -n \
--arg model "$MODEL" \
'{
  model: $model,
  stream: true,
  messages: [
    {role: "user", content: "日本の首都はどこ？一言で。"}
  ]
}' |
curl -N "http://localhost:${PORT:-8000}/v1/chat/completions" \
-H 'Content-Type: application/json' \
--data-binary @-
```

### max_completion_tokens

```sh
jq -n \
--arg model "$MODEL" \
'{
  model: $model,
  messages: [
    {role: "user", content: "python について説明してください。"}
  ],
  max_completion_tokens: 50
}' |
curl -sS http://localhost:${PORT:-8000}/v1/chat/completions \
-H 'Content-Type: application/json' \
--data-binary @- |
jq -r '.choices[0].message.content'
# Python（パイソン）は、世界で最も人気のある汎用プログラミング言語の一つです。その最大の特徴は**「書きやすさ」と「読みやすさ」**であり、初心者からプロのエンジニアまで幅広く使われています。
#
# 以下に、
```

### tool_call

```sh
jq -n \
--arg model "$MODEL" \
'{
  model: $model,
  messages: [
    {role: "user", content: "東京と大阪の天気は?タイマーを30秒にセットして。"}
  ],
  tools: [
    {
      type: "function",
      function: {
        name: "get_weather",
        parameters: {
          type: "object",
          properties: {
            location: {type: "string"}
          },
          required: ["location"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "set_timer",
        parameters: {
          type: "object",
          properties: {
            seconds: {type: "integer"}
          },
          required: ["seconds"]
        }
      }
    }
  ]
}' |
curl -sS http://localhost:${PORT:-8000}/v1/chat/completions \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '.choices[0].message.tool_calls'
# [
#   {
#     "id": "call_5bf5c0b6ecbd4944bfaba514",
#     "type": "function",
#     "function": {
#       "name": "get_weather",
#       "arguments": "{\"location\": \"東京\"}"
#     }
#   },
#   {
#     "id": "call_9f98db50e2ec4d1898710972",
#     "type": "function",
#     "function": {
#       "name": "get_weather",
#       "arguments": "{\"location\": \"大阪\"}"
#     }
#   },
#   {
#     "id": "call_786091eb2e2547b29eb96b35",
#     "type": "function",
#     "function": {
#       "name": "set_timer",
#       "arguments": "{\"seconds\": 30}"
#     }
#   }
# ]
```

### tool_choice

tool_choice は下記の 3 パターンで指定可能。
- `auto`: モデルにツール選択を任せる（デフォルト）
- `any` | `required`: ツール選択を強制（ツールが複数ある場合はモデルが選ぶ）
- `{"type":"function","function":{"name":...}}`: 特定のツール呼び出しを強制

#### auto

```sh
jq -n \
--arg model "$MODEL" \
'{
  model: $model,
  messages: [
    {role: "user", content: "こんにちは"}
  ],
  tools: [
    {
      type: "function",
      function: {
        name: "get_weather",
        parameters: {
          type: "object",
          properties: {
            location: {type: "string"}
          },
          required: ["location"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "set_timer",
        parameters: {
          type: "object",
          properties: {
            seconds: {type: "integer"}
          },
          required: ["seconds"]
        }
       }
     }
   ]
}' |
curl -sS http://localhost:${PORT:-8000}/v1/chat/completions \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '.choices[0].message'
# {
#   "role": "assistant",
#   "content": "こんにちは！今日はどんなお手伝いが必要ですか？"
# }
```

#### any / required

```sh
jq -n \
--arg model "$MODEL" \
'{
  model: $model,
  messages: [
    {role: "user", content: "こんにちは"}
  ],
  tools: [
    {
      type: "function",
      function: {
        name: "get_weather",
        parameters: {
          type: "object",
          properties: {
            location: {type: "string"}
          },
          required: ["location"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "set_timer",
        parameters: {
          type: "object",
          properties: {
            seconds: {type: "integer"}
          },
          required: ["seconds"]
        }
       }
     }
   ],
   tool_choice: "any"
}' |
curl -sS http://localhost:${PORT:-8000}/v1/chat/completions \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '.choices[0].message'
# {
#   "role": "assistant",
#   "content": null,
#   "tool_calls": [
#     {
#       "id": "call_d9fc6f940c23476c98e2b2a8",
#       "type": "function",
#       "function": {
#         "name": "get_weather",
#         "arguments": "{\"location\": \"Tokyo\"}"
#       }
#     }
#   ]
# }
```

#### specific

```sh
jq -n \
--arg model "$MODEL" \
'{
  model: $model,
  messages: [
    {role: "user", content: "こんにちは"}
  ],
  tools: [
    {
      type: "function",
      function: {
        name: "get_weather",
        parameters: {
          type: "object",
          properties: {
            location: {type: "string"}
          },
          required: ["location"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "set_timer",
        parameters: {
          type: "object",
          properties: {
            seconds: {type: "integer"}
          },
          required: ["seconds"]
        }
       }
     }
   ],
   tool_choice: {
     type: "function",
     function: {name: "get_weather"}
   }
}' |
curl -sS http://localhost:${PORT:-8000}/v1/chat/completions \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '.choices[0].message'
# {
#   "role": "assistant",
#   "content": null,
#   "tool_calls": [
#     {
#       "id": "call_b4df9a6d995c4735b8f10387",
#       "type": "function",
#       "function": {
#         "name": "get_weather",
#         "arguments": "{\"location\": \"Tokyo\"}"
#       }
#     }
#   ]
# }
```
> [!NOTE]
> any/required や specific は、文脈に関係なくツールを呼び出します
> あまりに文脈と乖離したツールしかない場合、特に `qwen3-omni` では不正なレスポンスが生成されがちです

### parallel_tool_calls

parallel_tool_calls は、デフォルトが `true` です。
単一のツール呼び出しを強制したいときは、`parallel_tool_calls: false` を指定します。

```sh
jq -n \
--arg model "$MODEL" \
'{
  model: $model,
  messages: [
    {role: "user", content: "東京と大阪の天気は?"}
  ],
  tools: [
    {
      type: "function",
      function: {
        name: "get_weather",
        parameters: {
          type: "object",
          properties: {
            location: {type: "string"}
          },
          required: ["location"]
        }
      }
    }
  ],
  parallel_tool_calls: false
}' |
curl -sS http://localhost:${PORT:-8000}/v1/chat/completions \
-H 'Content-Type: application/json' \
--data-binary @- |
jq '.choices[0].message'
# {
#   "role": "assistant",
#   "content": null,
#   "tool_calls": [
#     {
#       "id": "call_060acbd57cfe4c4eb8464158",
#       "type": "function",
#       "function": {
#         "name": "get_weather",
#         "arguments": "{\"location\": \"東京\"}"
#       }
#     }
#   ]
# }
```

### continuation

system, user, assistant, tool, assistant, human...  のような複数ターンのメッセージを処理する。

```sh
jq -n \
--arg model "$MODEL" \
'{
  model: $model,
  messages: [
    {role: "system", content: "語尾に「にゃ」をつけて答えてください"},
    {role: "user", content: "こんにちは"},
    {role: "assistant", content: "こんにちはにゃ！何かお手伝いできることはありますかにゃ？"},
    {role: "user", content: "今日の天気は？"},
    {role: "assistant", tool_calls: [
      {
        id: "call_123",
        type: "function",
        function: {
          name: "get_weather",
          arguments: "{\"location\": \"Tokyo\"}"
        }
      }
    ]},
    {role: "tool", content: "東京の天気は晴れ、最高気温25度、最低気温15度です。"}
  ],
  tools: [
    {
      type: "function",
      function: {
        name: "get_weather",
        parameters: {
          type: "object",
          properties: {
            location: {type: "string"}
          },
          required: ["location"]
        }
      }
    }
  ]
}' |
curl -sS http://localhost:${PORT:-8000}/v1/chat/completions \
-H 'Content-Type: application/json' \
--data-binary @- |
jq -r '.choices[0].message'
# {
#   "role": "assistant",
#   "content": "東京の天気は晴れ、最高気温25度、最低気温15度ですにゃ！"
# }
```

### image

```sh
jq -n \
--arg model "$MODEL" \
--rawfile img <(base64 -i tests/assets/miineko.png | tr -d '\n') \
'{
  model: $model,
  messages: [
    {role: "user", content: [
      {type: "image_url", image_url: {url: "data:image/png;base64,\($img)"}},
      {type: "text", text: "この画像を一言で説明して"}
    ]}
  ]
}' |
curl -sS http://localhost:${PORT:-8000}/v1/chat/completions \
-H 'Content-Type: application/json' \
--data-binary @- | jq -r '.choices[0].message.content'
# 「ピクセルアートで描かれたピンクの猫の顔」
```

### audio

```sh
jq -n \
--rawfile audio <(base64 -i tests/assets/song.wav | tr -d '\n') \
'{
  model: "qwen3-omni",
  messages: [
    {
      role: "user",
      content: [
        {type: "input_audio", input_audio: {data: $audio, format: "wav"}},
        {type: "text", text: "この audio の歌詞を短く引用してください。また、この音楽の雰囲気や構成も1文で説明してください。"}
      ]
    }
  ]
}' |
curl -sS "http://localhost:${PORT:-8000}/v1/chat/completions" \
-H 'Content-Type: application/json' \
--data-binary @- | jq -r '.choices[0].message.content'
# **歌詞の引用:**
# 「加速する世界の片端から君の声が聞こえてくる。揺れる心抱えながら、一歩ずつ前を向いて…」
#
# **雰囲気・構成の説明:**
# 電子音と力強いシンセポップのギターが交錯し、情熱的で懐かしさを感じさせるメロディーが特徴的な楽曲です。
```

> [!NOTE]
> audio 入力は `qwen3-omni` のみサポート。

### video

**映像のみ:**
```sh
jq -n \
--rawfile video <(base64 -i tests/assets/pv.mp4 | tr -d '\n') \
'{
  model: "qwen3-omni",
  messages: [
    {
      role: "user",
      content: [
        {type: "video_url", video_url: {url: "data:video/mp4;base64,\($video)"}},
        {type:"text",text:"この video の映像の展開を一文で説明してください。"}
      ]
    }
  ],
  use_audio_in_video: false,
  max_completion_tokens: 6000
}' |
curl -sS "http://localhost:${PORT:-8000}/v1/chat/completions" \
-H 'Content-Type: application/json' \
--data-binary @- | jq -r '.choices[0].message.content'
# ピンクのピクセルアートのクマが草原の小道を歩き、川を渡って村に到着しました。
```

**映像 + 音声:**
```sh
jq -n \
--rawfile video <(base64 -i tests/assets/pv.mp4 | tr -d '\n') \
'{
  model: "qwen3-omni",
  messages: [
    {
      role: "user",
      content: [
        {type: "video_url", video_url: {url: "data:video/mp4;base64,\($video)"}},
        {type:"text",text:"この video の音声には歌がありますか？ある場合は聞き取れる歌詞の一部を短く引用し、映像の展開も一文で説明してください。"}
      ]
    }
  ],
  max_completion_tokens: 6000
}' |
curl -sS "http://localhost:${PORT:-8000}/v1/chat/completions" \
-H 'Content-Type: application/json' \
--data-binary @- | jq -r '.choices[0].message.content'
# はい、歌があります。
#
# **聞き取れる歌詞の一部**:
# 加速する世界の中から
# 君の声が聞こえてくる
# 揺れる心を抱えながら
# 一歩ずつ前を向いて
#
# **映像の展開**:
# ピクセルアートのピンクのクマが画面を下から登場し、カメラが後退して広大な色鮮やかな村の風景を捉えます。
```

> [!NOTE]
> video 入力は `qwen3-omni` のみサポート。

### video (not use audio) + audio

```bash
jq -n \
--rawfile video <(base64 -i tests/assets/pv.mp4 | tr -d '\n') \
--rawfile audio <(base64 -i tests/assets/song.wav | tr -d '\n') \
'{
  model: "qwen3-omni",
  messages: [
    {
      role: "user",
      content: [
        {type: "video_url", video_url: {url: "data:video/mp4;base64,\($video)"}},
        {type: "input_audio", input_audio: {data: $audio, format: "wav"}},
        {type: "text", text: "audio から聞き取れる歌詞の一部を短く引用してください。また、video の映像の展開も一文で説明してください。"}
      ]
    }
  ],
  use_audio_in_video: false,
  max_completion_tokens: 6000
}' |
curl -sS "http://localhost:${PORT:-8000}/v1/chat/completions" \
-H 'Content-Type: application/json' \
--data-binary @- | jq -r '.choices[0].message.content'
# **歌詞の一部の短く引用:**
# 「加速する世界の中で
# 君の声が聞こえてくる
# 揺れる心抱えながら
# 一歩ずつ前を向いて」
#
# **video の映像の展開:**
# アニメのキャラクターが、暖かみのある居酒屋で複数のビールを前に楽しそうに笑いながら手を振るシーン。
```

> [!NOTE]
> `qwen3-omni` は audio と video の part を受け付ける。
> Qwen3-Omni は 1 リクエストにつき audio 入力を最大 *1 つ* しか使わない。
> video に音声があれば自動で demux されて audio として数えられるため、
> 音声付き video と別の audio part を同時に渡さないこと。

### video + image

> [!NOTE]
> 事前に ffmpeg で1秒間隔のフレーム画像を抽出しておく例:
> mkdir -p tests/assets/pv_frames
> ffmpeg -y -i tests/assets/pv.mp4 -vf fps=1 -start_number 1 tests/assets/pv_frames/t%d.jpg

```sh
jq -n \
--rawfile video <(base64 -i tests/assets/pv.mp4 | tr -d '\n') \
--slurpfile frames <(
  for i in {1..30}; do
    jq -n --arg i "$i" --rawfile img <(base64 -i "tests/assets/pv_frames/t${i}.jpg" | tr -d '\n') '
      [
        {type: "text", text: "t=[\($i)秒]"},
        {type: "image_url", image_url: {url: "data:image/jpeg;base64,\($img)"}}
      ]
    '
  done | jq -s 'flatten'
) \
'{
  model: "qwen3-omni",
  messages: [
    {
      role: "user",
      content: (
        [
          {type: "text", text: "まず動画と音声です。"},
          {type: "video_url", video_url: {url: "data:video/mp4;base64,\($video)"}},
          {type: "text", text: "次に、同じ動画から1秒間隔で抜き出した秒数ラベル付きフレームです。"}
        ]
        + $frames[0]
        + [
          {type: "text", text: "この video の歌詞の一部を短く引用してください。次に、最も印象的・象徴的な瞬間の秒数(t=◯秒)を1つ選んで、その理由を1文で説明してください。"}
        ]
      )
    }
  ],
  max_completion_tokens: 6000
}' | \
curl -sS "http://localhost:${PORT:-8000}/v1/chat/completions" \
-H 'Content-Type: application/json' \
--data-binary @- | jq -r '.choices[0].message.content'
# 詞（一部）: 「加速する世界の中から君の声が聞こえてくる」
#
# 最も印象的で象徴的な瞬間: t=12秒
#
# 説明: 一匹の小さなトカゲが登場し、物語の始まりや新たな道のりを象徴している。
```

> [!NOTE]
> frame 画像が多いと、レスポンスが不安定になりがち。

### video + image + tools

```sh
jq -n \
--rawfile video <(base64 -i tests/assets/pv.mp4 | tr -d '\n') \
--slurpfile frames <(
  for i in {1..30}; do
    jq -n --arg i "$i" --rawfile img <(base64 -i "tests/assets/pv_frames/t${i}.jpg" | tr -d '\n') '
      [
        {type: "text", text: "t=\($i)秒"},
        {type: "image_url", image_url: {url: "data:image/jpeg;base64,\($img)"}}
      ]
    '
  done | jq -s 'flatten'
) \
'{
  model: "qwen3-omni",
  tools: [
    {
      type: "function",
      function: {
        name: "record_highlight",
        description: "動画の中で最も印象的な瞬間の秒数と、その理由を記録する",
        parameters: {
          type: "object",
          properties: {
            timestamp_seconds: {
              type: "integer",
              description: "最も印象的なフレームの秒数（t=◯秒の◯）"
            },
            reason: {
              type: "string",
              description: "その瞬間が印象的な理由（映像と楽曲の両面から）"
            }
          },
          required: ["timestamp_seconds", "reason"]
        }
      }
    }
  ],
  tool_choice: {
    type: "function",
    function: {name: "record_highlight"}
  },
  messages: [
    {
      role: "user",
      content: (
        [
          {type: "text", text: "まず動画と音声です。"},
          {type: "video_url", video_url: {url: "data:video/mp4;base64,\($video)"}},
          {type: "text", text: "次に、同じ動画から1秒間隔で抜き出した秒数ラベル付きフレームです。"}
        ]
        + $frames[0]
        + [
          {type: "text", text: "映像・楽曲・フレームを分析し、最も印象的・象徴的な瞬間を一つ選んでください。選んだら、その秒数と、その理由を、1文で説明してください。"}
        ]
      )
    }
  ],
  max_completion_tokens: 6000
}' | \
curl -sS "http://localhost:${PORT:-8000}/v1/chat/completions" \
-H 'Content-Type: application/json' \
--data-binary @- | jq -r '.choices[0].message'
# {
#   "role": "assistant",
#   "content": null,
#   "tool_calls": [
#     {
#       "id": "call_58247d6050ca4d11a10fabcc",
#       "type": "function",
#       "function": {
#         "name": "record_highlight",
#         "arguments": "{\"timestamp_seconds\":27, \"reason\": \"この瞬間のカメラの位置が最も安定しており、森の小道を歩くキリンと村の景色をバランスよく捉えており、物語の世界観を象徴的に表現している。\"}"
#       }
#     }
#   ]
# }
```
