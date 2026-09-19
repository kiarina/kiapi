# chat

[mlx-vlm](https://github.com/Blaizzy/mlx-vlm) provides an OpenAI-compatible chat completion API.

- **vlm** (text + image):
  - Qwen3.8-27B-4bit
  - Qwen3.6-27B-4bit
- **omni** (text + image + audio + video):
  - Qwen3-Omni-30B-A3B-Instruct-4bit

It supports the following functions.

- streaming
- tool call
- tool choice (auto, any, specific)
- parallel tool calls
- automatic prefix caching for Qwen3.6 / Qwen3.8 text and image requests, and Qwen3-Omni text, image, audio, and video requests

## Automatic Prefix Caching

Qwen3.6, Qwen3.8, and Qwen3-Omni reuse matching prefixes from earlier
requests. Qwen3.6 / Qwen3.8 support text and images; Omni also supports audio,
video, and image + video. This reduces prefill latency when clients resend
stable system messages, tool schemas, or conversation history with media.
Responses are never cached, and `usage.prompt_tokens` reports the complete
logical prompt.

With the pinned mlx-vlm fork used by this checkout, Qwen3.8 reuses unchanged
history when images are appended, and Omni does the same for images, audio clips,
videos and mixtures. Each checkpoint identifies only the processed media content,
grid/length, positions and video FPS inside that prefix. After a hit, only suffix
media is encoded. Changing or reordering old media invalidates checkpoints
containing it; an earlier checkpoint may still hit. Downloading, decoding and
preprocessing still run before lookup.

Omni supports multiple independent audio clips, including audio tracks demuxed
from videos by `use_audio_in_video`. Each clip is extracted and encoded
independently so a longer appended clip cannot change old audio features.
Native mlx-vlm audiovisual token interleaving is excluded from prefix reuse;
kiapi uses its existing separate video/audio representation instead.

Qwen3.6 retains whole-request media identity: ordered SHA-256 content hashes,
independent of temporary paths. Adding or replacing its media recomputes the full
prompt. All models avoid restoring a checkpoint inside a media span.

The source checkout pins [Omni PR #2311](https://github.com/Blaizzy/mlx-vlm/pull/2311),
built on [Qwen image PR #2309](https://github.com/Blaizzy/mlx-vlm/pull/2309), at
`98300012bbccc728d0a98e92444cc45bc433e284` through `tool.uv.sources`.
Published kiapi wheels still depend on official mlx-vlm 0.7.1. Without the new
engine capability, handlers retain conservative whole-request media invalidation;
multiple audio clips also require the pinned fork. No request API or new user
setting is needed.

A hit also requires a matching stored checkpoint. Qwen3.6 removes its empty
thinking prefill from historical assistant turns, so continuing a short image
conversation can miss even when the image is unchanged; repeating the same
request still hits.

The cache is scoped to each loaded model, remains in memory only, and is
released with the model. Hits and memory use are written to the server log as
`cached_tokens`, `prompt_tps`, `resident_bytes`, and aggregate stats.
Responses report reused tokens in the OpenAI-compatible
`usage.prompt_tokens_details.cached_tokens` field. For streaming requests, set
`stream_options.include_usage: true` to receive usage in a final chunk with an
empty `choices` array before `[DONE]`.

| Setting | Environment variable | Default | Description |
|---|---|---:|---|
| `apc_enabled` | `KIAPI_CHAT_APC_ENABLED` | `true` | Enable APC for supported inputs. |
| `apc_num_blocks` | `KIAPI_CHAT_APC_NUM_BLOCKS` | `2048` | Maximum blocks per loaded model. |
| `apc_block_size` | `KIAPI_CHAT_APC_BLOCK_SIZE` | `16` | Tokens per block. |
| `apc_memory_max_gb` | `KIAPI_CHAT_APC_MEMORY_MAX_GB` | `4.0` | Estimated resident-memory limit per model. |
| `apc_tenant` | `KIAPI_CHAT_APC_TENANT` | `default` | Server-controlled isolation salt. |

Changing the tenant makes existing entries unreachable. Disable APC to fall
back to normal generation. Disk persistence is intentionally not enabled, so a
server restart starts with an empty prefix cache. Model eviction, TTL expiration,
and shutdown release the cache. The memory budget includes idle models' retained
cache bytes and the active model's configured cache capacity plus generation margin.

Disk persistence was evaluated and remains disabled: it adds reuse after eviction
or restart, but does not accelerate an existing memory hit. Its files contain
recoverable prompt token IDs in plaintext metadata, its capacity limit is eventual
and per namespace, and some malformed headers escape the corruption fallback.
There is no kiapi disk-cache setting; upstream `APC_DISK_*` environment variables
do not enable disk storage in kiapi.

GPU regression measurements (stop the service first):

```sh
uv run python scripts/capabilities/measure_chat_apc.py qwen3.8-27b --output .verify/apc/qwen38.json
uv run python scripts/capabilities/measure_chat_apc.py qwen3-omni --output .verify/apc/omni.json
uv run python scripts/capabilities/measure_chat_apc_disk.py
```

The measurements include cold/warm responses, partial hits, changed media/options,
long visual prompts, memory release, and reloading. Inspect response semantics in
the JSON artifacts; floating-point differences can change wording on cache hits.

## Prefill chunk sizing

kiapi retains mlx-vlm's 2048-token prefill step. Chunk size is separate from
APC block size and checkpoint spacing. On the measured Qwen3.8-27B-4bit / M4 Max
4K and 16K inputs, changing only chunk size did not meaningfully reduce cold
prefill latency. Larger chunks used more peak memory.

See the [benchmark procedure and results](../../../../docs/playbooks/chat-prefill-benchmark.md)
for reproducible comparisons, including image-prefix APC checks.

## Client Disconnects

When a streaming or non-streaming client disconnects, its chat job requests
cancellation. A queued job is skipped; generation already producing output
stops at the next token boundary. Canceling a request that uses APC clears that
model's prefix cache because mlx-vlm 0.7.1 otherwise retains internal block
leases when its generator closes early.

Long prompt prefill is not immediately interruptible. mlx-vlm 0.7.1 does not
expose a cancellation callback inside chunked prefill, so cancellation takes
effect when prefill returns the first generated token. HTTP sync timeout remains
different from a disconnect: a timed-out job continues and can be polled.

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

| Model | License | Terms | Size | Mem | Description |
|---|---|---|---:|---:|---|
| [mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit) | Apache-2.0 | Not required | 21.8 GB | ~24 GB | `qwen3-omni` (default). text + image + audio + video, tool-call prefill=JSON. Talker (audio *output*) is private and only outputs text/tool-calls. Maximum of **1** audio input per request (including demux audio for video with audio). |
| [mlx-community/Qwen3.8-27B-4bit](https://huggingface.co/mlx-community/Qwen3.8-27B-4bit) | Apache-2.0 | Not required | 16.1 GB | ~20 GB | `qwen3.8-27b`. Same handler as `qwen3.6-27b` (`model_type: qwen3_5`): text + image only, tool-call prefill=Hermes/XML. Reasoning is OFF by default. |
| [mlx-community/Qwen3.6-27B-4bit](https://huggingface.co/mlx-community/Qwen3.6-27B-4bit) | Apache-2.0 | Not required | 16.1 GB | ~19 GB | `qwen3.6-27b`. text + image only, tool-call prefill=Hermes/XML. Reasoning is OFF by default. |

- **HTTP 400** when sending a part of a modality that is not supported by the selected model.

## Notes

Chat is implemented using **mlx-vlm**, but some patches have been added to avoid bugs.
Please be aware that this patch may break with updates to **mlx-vlm**.

**mlx-vlm** is fixed to `mlx-vlm==0.7.1`.
Patches E (streaming UTF-8) and G (`mx.repeat` count) were removed at 0.7.1, where upstream fixed both.
When updating, please reconfirm the contents of the patch below and make corrections as necessary.
Details are in the docstring.

| # | Contents | Location | Target models |
|---|------|------|------------|
| A | Pass audio as a float32 array instead of a path | `_models/qwen3_omni.py` | omni |
| B | Avoid stereo audio resampling inconsistency by loading it yourself | `_utils/load_audio_mono.py` | omni |
| C | Join the image and video deepstack rows by position | `_operations/ensure_omni_image_video_join.py` | omni (image+video simultaneously) |
| F | Text recovery from token ID (stream) | `_operations/stream_text_from_tokens.py` | qwen3.6 / qwen3.8 (stream) |
| H | Window the deepstack inputs per prefill chunk | `_operations/ensure_omni_deepstack_window.py` | omni (image / video) |

**A. Pass the audio as a float32 array:**
- **Location**: `run`(`audio_arrays = [load_audio_mono(p, sr=sr) ...]`) in `_models/qwen3_omni.py`
- **Reason**: Audio is loaded by kiapi (`load_audio_mono`, see B) and passed as arrays. mlx-vlm 0.6.x crashed
  on raw audio paths (`could not convert string to float`); 0.7.1 accepts paths but loads them through the
  buggy `load_audio` of B, so arrays are still required.
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
- **Upstream fix**: [Blaizzy/mlx-vlm#2258](https://github.com/Blaizzy/mlx-vlm/pull/2258) downmixes before
  resampling. Once it ships, A and B can be dropped together.

**C. Join the image and video deepstack rows by position:**
- **Location**: `_operations/ensure_omni_image_video_join.py` (called at the beginning of `run` in `_models/qwen3_omni.py`)
- **Reason**: With an image and a video in one prompt, `Thinker.get_input_embeddings` of mlx-vlm 0.7.1 joins the two
  deepstack feature sets with the one-argument `mx.where(mask)[0]` and a free-function `mx.scatter`, which mlx does not
  provide (`TypeError`). It also `take`s rows from each modality's embeds using positions in the joint sequence, so the
  video rows are read from the wrong offsets. (The earlier version of this patch grafted `mx.where` / `mx.scatter` onto
  `mlx.core` and so kept that second bug.) Upstream fix: [Blaizzy/mlx-vlm#2257](https://github.com/Blaizzy/mlx-vlm/pull/2257).
- **Workaround**: Replace only that block of the method with the #2257 version, which assigns each modality's embeds whole
  at its own positions, as the reference implementation does. The patch changes nothing if the upstream block no longer
  matches; the unit test fails in that case so the pin cannot move silently.
- **Trigger**: Only when image and video are passed to omni **at the same time**.

**F. Text recovery from token ID (qwen3.6 / qwen3.8 stream):**
- **Location**: `_operations/stream_text_from_tokens.py`
- **Reason**: More of a compatibility wrapper than a bug avoidance. `_ServerTokenStreamer` / in mlx-vlm
  If `make_streaming_detokenizer` is available, it will extract the text from the token ID.
  Restore. If it is not available, pass through (`yield from chunks`).

**H. Window the deepstack inputs per prefill chunk:**
- **Location**: `_operations/ensure_omni_deepstack_window.py` (called at the beginning of `run` in `_models/qwen3_omni.py`)
- **Reason**: mlx-vlm 0.7.1 passes the full-prompt `visual_pos_masks` and `deepstack_visual_embeds` to every
  prefill chunk (2048 tokens by default) and to the final one-token step. Omni's `_deepstack_process` scatters at
  full-prompt positions into the shorter chunk and writes past the end of the GPU buffer. A 28-frame video
  (3611 prompt tokens) decodes `!!!!…` or aborts the server with
  `[METAL] Command buffer execution failed: Caused GPU Address Fault Error` (upstream issue #2099,
  fix proposed in [Blaizzy/mlx-vlm#2256](https://github.com/Blaizzy/mlx-vlm/pull/2256)).
  Short image prompts overrun by one row and usually survive.
- **Workaround**: Wrap Omni's decoder (`Qwen3VLMoEModel.__call__`) and slice the mask to the current window and
  the embeds to the visual tokens in that window, the same way the Qwen3-VL language model already does.
  Batched generation with per-row offsets skips deepstack instead.
- **Trigger**: Any Omni image or video input (harmful once the prompt exceeds one prefill chunk).


## Quickstart
```bash
MODEL=qwen3.8-27b
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

### Omni APC compatibility (mlx-vlm 0.7.1)

For official mlx-vlm 0.7.1, `ensure_omni_apc_embeddings` adds nested thinker image/video/audio token IDs to
APC's safe-boundary detection. On a restored text suffix it preserves the complete
prompt's RoPE positions and skips re-encoding media; upstream otherwise attempts
to apply full media grids to the short suffix and can raise an index error.
Omni uses compact, layer-major snapshots for media-safe restoration. This is
verified together with patches C and H on visual prompts longer than 2048 tokens.
The pinned fork owns this restoration and advertises its media-prefix capability,
so kiapi skips the old text-suffix-only embedding wrapper. Re-check this workaround
when upgrading mlx-vlm.

### Pinned-fork compatibility

The pinned upstream base already fixes Omni's combined image/video join and uses
expanded `[batch, tokens, layers, hidden]` deepstack residuals. Patch C therefore
becomes a no-op, and patch H skips this representation. Both compatibility paths
remain for official mlx-vlm 0.7.1 installations. The full chat verification covers
both the new Qwen3.8 prefix path and Omni on the pinned fork.
