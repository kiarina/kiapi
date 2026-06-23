# chat

**English** | [日本語](README.ja.md)

[mlx-vlm](https://github.com/Blaizzy/mlx-vlm) provides an OpenAI-compatible chat completion API.

- **vlm** (text + image):
  - Qwen3.6-27B-4bit
- **omni** (text + image + audio + video):
  - Qwen3-Omni-30B-A3B-Instruct-4bit

It supports the following functions.

- streaming
- tool call
- tool choice (auto, any, specific)
- parallel tool calls

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/chat/completions` | Chat Completions | OpenAI-compatible Chat Completions API. |
| `GET /v1/models` | Model list | Returns a list of available models. |
| `GET /v1/chat/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

- Unique extensions:
  - `fps`: Conversion frame rate of video
  - `use_audio_in_video`: Whether to include audio in video in model input

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/chat/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/chat/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/chat/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mlx-vlm](https://github.com/Blaizzy/mlx-vlm) | MIT | Drive Qwen multimodal models on MLX. |

## Models

| Model | License | Terms | Size | Description |
|---|---|---|---:|---|
| [mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit) | Apache-2.0 | Not required | 21.8 GB | `qwen3-omni` (default). text + image + audio + video, tool-call prefill=JSON. Talker (audio *output*) is private and only outputs text/tool-calls. Maximum of **1** audio input per request (including demux audio for video with audio). |
| [mlx-community/Qwen3.6-27B-4bit](https://huggingface.co/mlx-community/Qwen3.6-27B-4bit) | Apache-2.0 | Not required | 16.1 GB | `qwen3.6-27b`. text + image only, tool-call prefill=Hermes/XML. Reasoning is OFF by default. |

- **HTTP 400** when sending a part of a modality that is not supported by the selected model.

## Notes

Chat is implemented using **mlx-vlm**, but some patches have been added to avoid bugs.
Please be aware that this patch may break with updates to **mlx-vlm**.

**mlx-vlm** is fixed to `mlx-vlm==0.6.3`.
When updating, please reconfirm the contents of the patch below and make corrections as necessary.
Details are in the docstring.

| # | Contents | Location | Target models |
|---|------|------|------------|
| A | Pass audio as a float32 array instead of a path | `_models/qwen3_omni.py` | omni |
| B | Avoid stereo audio resampling inconsistency by loading it yourself | `_utils/load_audio_mono.py` | omni |
| C | `mx.where` / `mx.scatter` shim for mlx 0.31.x | `_models/qwen3_omni.py` `_ensure_mlx_compat` | omni (image+video simultaneously) |
| E | UTF-8 decoding relaxation for streaming detokenizer | `_operations/ensure_streaming_detokenizer_compat.py` | Both models (stream) |
| F | Text recovery from token ID (stream) | `_operations/stream_text_from_tokens.py` | qwen3.6 (stream) |

**A. Pass the audio as a float32 array:**
- **Location**: `run`(`audio_arrays = [load_audio_mono(p, sr=sr) ...]`) in `_models/qwen3_omni.py`
- **Reason**: The qwen3-omni branch of mlx-vlm fails when it receives the raw audio **path**
  Crash with `could not convert string to float`. `generate(audio=...)` has
  You need to pass ndarray.
- **Trigger**: All cases where omni has audio input.

**B. Stereo audio resample mismatch:**
- **Location**: `_utils/load_audio_mono.py` (Load the array of A using this own function)
- **Reason**: There is a bug in `utils.load_audio` of mlx-vlm. `read_audio` reads the audio
  `(samples, channels)` (channel last) is returned, but `load_audio` is
  - Resample to `resample_audio(..., axis=-1)` = **channel axis**,
  - Downmix `mean(axis=1)` = same channel axis
  The handling of the axis is inconsistent. The result is **stereo audio with different rates** (typically
  48kHz / 44.1kHz stereo wav), the time axis is not resampled, and the 48kHz sample is
  It is passed to omni as 16kHz, and the audio cannot be recognized. Mono is one dimensional
  `axis=-1` happens to be the time axis, so it works correctly.
- **Workaround**: `load_audio_mono` **converts to monaural first and then resamples**, so
  The default `axis=-1` of `resample_audio` is always the time axis and rate conversion is performed correctly.
  (48k mono / 48k stereo / 44.1k stereo / 16k stereo all to 16000 samples).
- **Impact on audio in video**: None. `_extract_audio` in `_operations/parse_messages.py`
To demux to monaural 16kHz from the beginning with ffmpeg `-ac 1 -ar 16000`,
  Resample/downmix itself does not occur and does not fall under the bug condition.

**C. mlx 0.31.x compatible shim (`mx.where` / `mx.scatter`):**
- **Location**: `_ensure_mlx_compat` in `_models/qwen3_omni.py` (called at the beginning of `run`)
- **Reason**: `qwen3_omni_moe/thinker.py` of mlx-vlm does not support **image + video at the same time.
  Input route** (visual_embeds_multiscale / deepstack join), present in mlx 0.31.x
  Use APIs that do not:
  - 1 argument format `mx.where(mask)[0]` (get index of True) → TypeError
  - Free function `mx.scatter(a, idx, vals, ax)` → AttributeError

  There is no problem with image alone/video alone using a different route. Do not rewrite site-packages and provide a compatible implementation.
  Avoid by grafting (idempotent/additive, no effect on other routes).
- **Trigger**: Only when image and video are passed to omni **at the same time**.

**E. UTF-8 decoding relaxation for streaming detokenizer:**
- **Location**: `_operations/ensure_streaming_detokenizer_compat.py` (called via stream route)
- **Reason**: `BPEStreamingDetokenizer.add_token` of mlx-vlm is
  Decode bytes using **strict UTF-8**. Invalid UTF-8 at flash boundaries
  Byte token string causes streaming response to crash. On the `finalize` side,
  The streaming route is also `errors="replace"` because it handles the same decoding tolerantly.
  Equivalently mitigate.
- **Trigger**: `stream=true` for both models.

**F. Text recovery from token ID (qwen3.6 stream):**
- **Location**: `_operations/stream_text_from_tokens.py`
- **Reason**: More of a compatibility wrapper than a bug avoidance. `_ServerTokenStreamer` / in mlx-vlm
  If `make_streaming_detokenizer` is available, it will extract the text from the token ID.
  Restore. If it is not available, pass through (`yield from chunks`).

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
Streaming:
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

tool_choice can be specified in the following 3 patterns.
- `auto`: Let the model select the tool (default)
- `any` | `required`: Force tool selection (if there are multiple tools, the model will choose)
- `{"type":"function","function":{"name":...}}`: Force a specific tool call

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
> any/required or specific calls the tool regardless of context
> If you only have tools that are too out of context, `qwen3-omni` in particular tends to generate incorrect responses

### parallel_tool_calls

parallel_tool_calls defaults to `true`.
If you want to force a single tool call, specify `parallel_tool_calls: false`.
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

Handle multi-turn messages like system, user, assistant, tool, assistant, human...
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
> Audio input is only supported by `qwen3-omni`.

### video

**Video only:**
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
**Video + Audio:**
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
> Video input is only supported by `qwen3-omni`.

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
> `qwen3-omni` accepts audio and video parts.
> Qwen3-Omni uses at most *one* audio input per request.
> If video has audio, it will be automatically demuxed and counted as audio, so
> Do not pass a video with audio and another audio part at the same time.

### video + image

> [!NOTE]
> Example of extracting frame images at 1 second intervals using ffmpeg in advance:
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
> If there are many frame images, the response tends to be unstable.

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
