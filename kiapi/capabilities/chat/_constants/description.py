DESCRIPTION = """OpenAI-compatible chat completions: multimodal, tool calling, streaming.

POST OpenAI Chat Completions to `/v1/chat/completions`.

## Upstream docs
- [mlx-vlm](https://github.com/Blaizzy/mlx-vlm) — the multimodal MLX engine kiapi runs
- [mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit) — `qwen3-omni` weights
- [mlx-community/Qwen3.6-27B-4bit](https://huggingface.co/mlx-community/Qwen3.6-27B-4bit) — `qwen3.6-27b` weights

## Choosing A Model
`model` selects a registered chat model (full catalog and aliases:
`GET /v1/chat/models`). The currently served models differ by input modality, so
choose by what you send:
- **qwen3-omni** (default) — text + image + **audio + video**. Use it for any
  audio/video input. On video with a sound track, the audio is auto-demuxed and
  also fed as audio, so the model both sees and hears the clip.
  there is no audio/speech output (Qwen3-Omni's Talker is not exposed).
- **qwen3.6-27b** — text + image only. Lighter on memory for text/image work;
  sending audio or video to it returns HTTP 400.

## Audio Input
Formats:
```json
{"type": "input_audio", "input_audio": {"data": "<base64>", "format": "wav"}}
```
Aliases accepting a source string (http(s) URL or data URL):
```json
{"type": "audio_url", "audio_url": {"url": "https://example.com/voice.mp3"}}
{"type": "audio_url", "audio_url": {"url": "data:audio/wav;base64,AAAA..."}}
{"type": "audio", "audio": "https://example.com/voice.wav"}
```
For bare base64, set `format` (e.g. `"wav"`, `"mp3"`) so the extension is known.

Qwen3-Omni uses at most one audio input per request (mlx-vlm limitation; extras
are ignored). A video's demuxed audio (below) counts toward this — don't also
pass a separate audio part alongside a sounded video.

## Video Input
Formats:
```json
{"type": "video_url", "video_url": {"url": "https://example.com/clip.mp4"}}
{"type": "video_url", "video_url": {"url": "data:video/mp4;base64,AAAA..."}}
```
Aliases accepting the same source string directly:
```json
{"type": "video", "video": "https://example.com/clip.mp4"}
{"type": "input_video", "input_video": "data:video/mp4;base64,AAAA..."}
{"type": "input_video", "input_video": {"data": "<base64>", "format": "mp4"}}
```
- **Frame sampling** — frames are sampled at `fps` (default 1.0). Lower it for
  long clips to cut token and memory cost.
- **Sound** — if the video carries an audio track it is auto-demuxed and fed as
  audio too (toggle with `use_audio_in_video`), so the model both sees and hears
  the clip. A separate audio part is then usually unnecessary.

## Defaults When Omitted
Fields left unset fall back to server-side defaults, not the `null` shown in the
schema:
- `max_completion_tokens`: 512 (capped at 4096)
- `temperature`: 0.7
- `top_p`: 1.0
- `fps`: 1.0 (video frame sampling)
- `use_audio_in_video`: true

## Limits
- The selected model must fit the global memory budget; if it can't even after
  evicting everything else, the request returns HTTP 503.
- Large/long videos cost a lot of tokens and memory; keep them short and/or lower
  `fps` (see Video Input).

## Reliability Tips
- For tool calling under heavy multimodal input, prefer `tool_choice=required`
  or a specific function — a plain "please call the tool" instruction is more
  likely to be ignored or malformed. `required`/specific choices prefill the
  assistant turn with `<tool_call>` so the model commits to a call.
- Interleave multiple images with text as separate ordered image parts; this
  works well.
- When streaming, plain text streams as the model emits chunks, but tool-call
  deltas are held until the call is parseable.

## Examples

### Text (default model)
```sh
curl -sS http://HOST:PORT/v1/chat/completions \\
  -H 'Content-Type: application/json' \\
  -d '{
    "messages": [{"role": "user", "content": "こんにちは"}]
  }'
```

### Image + text on qwen3.6-27b
```sh
curl -sS http://HOST:PORT/v1/chat/completions \\
  -H 'Content-Type: application/json' \\
  -d '{
    "model": "qwen3.6-27b",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "この画像を説明して"},
          {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0..."}}
        ]
      }
    ]
  }'
```

### Audio + video (omni model)
See Audio & Video Input for the source/sound rules. The video below carries its
own sound, so the `input_audio` part is shown only to illustrate inline base64.
```sh
curl -sS http://HOST:PORT/v1/chat/completions \\
  -H 'Content-Type: application/json' \\
  -d '{
    "model": "qwen3-omni",
    "fps": 1.0,
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "この動画で何が起きている? 音も踏まえて説明して"},
          {"type": "video_url", "video_url": {"url": "https://example.com/clip.mp4"}},
          {"type": "input_audio", "input_audio": {"data": "<base64>", "format": "wav"}}
        ]
      }
    ]
  }'
```

### Force a specific tool
```sh
curl -sS http://HOST:PORT/v1/chat/completions \\
  -H 'Content-Type: application/json' \\
  -d '{
    "messages": [{"role": "user", "content": "大阪の天気は?"}],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "parameters": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"]
          }
        }
      }
    ],
    "tool_choice": {"type": "function", "function": {"name": "get_weather"}}
  }'
```

### Disable Qwen3.6 thinking (OpenAI SDK)
```python
client.chat.completions.create(
    model="qwen3.6-27b",
    messages=[...],
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
```
"""
