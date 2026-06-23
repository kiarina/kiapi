DESCRIPTION = """Music generation (ACE-Step 1.5): compose, cover, repaint, extract.

Four operations on ACE-Step 1.5: `/generate` (text2music — a new song from a
style prompt + lyrics), `/cover` (re-style an existing track), `/repaint`
(regenerate a time range), and `/extract` (separate into stems). ACE-Step runs in
an isolated subprocess (it pins an older transformers than chat/embedding); the
first request after idle pays a load cost of tens of seconds, then it stays
resident until the idle TTL or budget pressure frees it.

## Upstream docs
- [ACE-Step](https://github.com/ace-step/ACE-Step) — the upstream model

## Models
- **xl-base** (default) — highest quality. 32 inference steps, CFG 7.0.
  ~25 s per 30 s of audio on M4 Max.
- **turbo** — fastest. 8 inference steps, no CFG. ~4 s per 15 s on M4 Max. Great
  for prototyping / iterating on prompts.

Pick the preset with `model`; discover variants at `GET /v1/audio/acestep/models`.
The sampling overrides (`inference_steps`, `guidance_scale`, `shift`) default to
the preset's tuned values — set them only to deviate.

## Source workflow
`/cover`, `/repaint`, and `/extract` operate on an existing track: POST the source
WAV to `/v1/files` to get a `file_id`, then pass it as `source`. `/generate` needs
no source.

## Prompt tips
Describe the SOUND, not the story — a narrative sentence beats a keyword list.
Useful elements to mention:
- **genre**: Modern J-Pop / Acoustic Jazz / Dark Trap / Lo-fi Hip-hop / Anime OST
- **tempo**: 132 BPM / slow and intimate / driving beat / half-time feel
- **instruments**: bright piano / smooth saxophone / 808 sub-bass / nylon guitar
- **vocal**: emotional female vocal / whispered delivery / powerful male tenor
- **mood**: melancholic / triumphant / cozy / aggressive / dreamy / nostalgic
- **production**: polished radio-ready / lo-fi vinyl texture / orchestral / live band

- **good**: "A melancholic piano ballad where soft female vocals weave through
  gentle strings, intimate and heartbreaking. 80 BPM."
- **bad**: "piano, sad, female, slow"

## Lyrics format (generate)
Use `[Square Bracket]` section tags at the start of a line: `[Intro]`,
`[Verse 1]`, `[Pre-Chorus]`, `[Chorus]`, `[Bridge]`, `[Instrumental]`, `[Outro]`.
Modifiers work too, e.g. `[Verse 1 - Female]`, `[Chorus - Both]`,
`[Bridge - Whispered]`. Set lyrics to `[Instrumental]` for no vocals. Keep the
lyric length proportionate to `duration` — sparse lyrics over a long duration
degrade quality.

## Language codes (lang, generate)
ISO 639-1: `ja` Japanese, `en` English, `ko` Korean, `zh` Mandarin, `yue`
Cantonese, `es` Spanish, `fr` French, `de` German, …. `unknown` auto-detects
(may reduce quality).

## TIPS
- For a quick track, call `sync` without `Accept: application/json` to get the raw
  WAV bytes straight back (`curl -o out.wav`). `/extract` is multi-artifact, so it
  always returns Job JSON.
- Reuse a `seed` (≠ -1) with the same params to reproduce a result.
- Run `kiapi activate` ahead of time so the first request doesn't pay a cold-start
  weight download.

## Examples

### Generate (sync, turbo)
```sh
jq -n \\
--arg prompt "Modern J-Pop, 132 BPM, bright piano, emotional electric guitar, upbeat drums, polished anime opening production" \\
--arg lyrics '[Verse 1]
加速する世界の中で
君の声が聴こえてくる

[Pre-Chorus]
夜明け前の空に
まだ見ぬ明日を描いた

[Chorus]
僕らは光を追いかける
終わらない夢の向こうへ
何度でも手を伸ばして
新しい風になる
' \\
'{
  "model": "turbo",
  "mode": "sync",
  "prompt": $prompt,
  "lyrics": $lyrics,
  "duration": 30,
  "lang": "ja",
  "seed": 1
}' |
curl -sS -X POST http://localhost:${PORT:-8000}/v1/audio/acestep/generate \\
  -H 'Content-Type: application/json' \\
  --data-binary @- \\
  -o acestep_generate.wav
```

### Cover (async, turbo)
```sh
curl -sS http://HOST:PORT/v1/audio/acestep/cover \\
  -H 'Content-Type: application/json' \\
  -d '{
    "model": "turbo",
    "mode": "async",
    "source": "<file_id>",
    "prompt": "lo-fi chillhop, warm tape",
    "strength": 0.7
  }'
# -> {"job_id": "..."}; poll GET /v1/jobs/{job_id}
```

### Extract stems
```sh
curl -sS http://HOST:PORT/v1/audio/acestep/extract \\
  -H 'Content-Type: application/json' \\
  -d '{
    "source": "<file_id>",
    "targets": ["vocals", "drums", "bass", "other"]
  }'
# -> one job, artifacts = 4 file_ids (one WAV per target)
```
"""
