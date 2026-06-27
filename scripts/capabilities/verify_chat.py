import base64
import json
import os
import sys
import time
from typing import Any

import httpx

BASE_URL = os.environ.get("KIAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
URL = f"{BASE_URL}/v1/chat/completions"
ASSETS = os.environ.get(
    "KIAPI_ASSETS_DIR",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "assets"
    ),
)
STREAM_MODES = [False, True]
TEST_PREFIXES = tuple(a for a in sys.argv[1:] if a != "--fast")


def post_chat(payload: dict) -> tuple[dict, float]:
    t0 = time.time()
    if payload.get("stream"):
        try:
            with httpx.stream("POST", URL, json=payload, timeout=1200.0) as r:
                r.raise_for_status()
                chunks = []
                for line in r.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        break
                    chunks.append(json.loads(data))
        except httpx.HTTPError as e:
            print(f"\n[HTTP ERROR] {e}")
            if hasattr(e, "response") and e.response is not None:
                print(e.response.text)
            sys.exit(1)

        dt = time.time() - t0
        try:
            return stream_chunks_to_completion(chunks), dt
        except RuntimeError as e:
            print(f"\n[STREAM ERROR] {e}")
            sys.exit(1)

    try:
        r = httpx.post(URL, json=payload, timeout=1200.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        print(f"\n[HTTP ERROR] {e}")
        if hasattr(e, "response") and e.response is not None:
            print(e.response.text)
        sys.exit(1)

    dt = time.time() - t0
    return r.json(), dt


def stream_chunks_to_completion(chunks: list[dict]) -> Any:
    """Fold OpenAI chat.completion.chunk SSE events into a completion-like dict."""
    if not chunks:
        return {
            "choices": [
                {"message": {"role": "assistant", "content": ""}, "finish_reason": None}
            ]
        }

    content_parts: list[str] = []
    tool_calls: list[dict] = []
    role = "assistant"
    finish_reason = None

    for chunk in chunks:
        if "error" in chunk:
            raise RuntimeError(chunk["error"])
        choice = chunk.get("choices", [{}])[0]
        finish_reason = choice.get("finish_reason") or finish_reason
        delta = choice.get("delta") or {}
        role = delta.get("role") or role
        if "content" in delta and delta["content"] is not None:
            content_parts.append(delta["content"])
        for call in delta.get("tool_calls") or []:
            while len(tool_calls) <= call.get("index", len(tool_calls)):
                tool_calls.append({})
            idx = call.get("index", len(tool_calls) - 1)
            merged = dict(tool_calls[idx])
            for key, value in call.items():
                if key == "function" and isinstance(value, dict):
                    fn = dict(merged.get("function") or {})
                    for fn_key, fn_value in value.items():
                        if fn_key == "arguments":
                            fn[fn_key] = fn.get(fn_key, "") + (fn_value or "")
                        else:
                            fn[fn_key] = fn_value
                    merged["function"] = fn
                elif key != "index":
                    merged[key] = value
            tool_calls[idx] = merged

    message = {"role": role}
    content = "".join(content_parts)
    if tool_calls:
        message["content"] = content or None  # type: ignore
        message["tool_calls"] = tool_calls  # type: ignore
    else:
        message["content"] = content

    return {
        "id": chunks[0].get("id"),
        "object": "chat.completion",
        "created": chunks[0].get("created"),
        "model": chunks[0].get("model"),
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def get_base64(path: str) -> str:
    with open(os.path.join(ASSETS, path), "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_frames() -> list[dict]:
    # assets/pv_frames にある .jpg を秒数順にソートして取得
    frames_dir = os.path.join(ASSETS, "pv_frames")
    frames = []  # type: ignore
    if not os.path.exists(frames_dir):
        return frames
    for f in sorted(os.listdir(frames_dir)):
        if f.startswith("t") and f.endswith(".jpg"):
            sec = f[1:-4]
            b64 = get_base64(f"pv_frames/{f}")
            frames.append(
                [
                    {"type": "text", "text": f"t={sec}秒"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ]
            )
    return frames  # type: ignore


def print_result(  # type: ignore
    title: str,
    expected_example: str,
    actual_output: dict | list | str | None,
    dt: float,
):
    print(f"\n{'=' * 70}")
    print(f"[{title}]  (time: {dt:.1f}s)")
    print("\n--- Expected Example (from README) ---")
    print(expected_example)
    print("\n--- Actual Output ---")
    if isinstance(actual_output, (dict, list)):
        print(json.dumps(actual_output, indent=2, ensure_ascii=False))
    else:
        print(str(actual_output).strip())
    print(f"{'=' * 70}")


# --- Common Tools for testing ---

TOOL_WEATHER = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "parameters": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
    },
}

TOOL_TIMER = {
    "type": "function",
    "function": {
        "name": "set_timer",
        "parameters": {
            "type": "object",
            "properties": {"seconds": {"type": "integer"}},
            "required": ["seconds"],
        },
    },
}

TOOL_HIGHLIGHT = {
    "type": "function",
    "function": {
        "name": "record_highlight",
        "description": "動画の中で最も印象的な瞬間の秒数と、その理由を記録する",
        "parameters": {
            "type": "object",
            "properties": {
                "timestamp_seconds": {
                    "type": "integer",
                    "description": "最も印象的なフレームの秒数（t=◯秒の◯）",  # noqa: RUF001
                },
                "reason": {
                    "type": "string",
                    "description": "その瞬間が印象的な理由（映像と楽曲の両面から）",  # noqa: RUF001
                },
            },
            "required": ["timestamp_seconds", "reason"],
        },
    },
}


# --- Test Cases ---


def with_stream(payload: dict, stream: bool) -> Any:
    payload = dict(payload)
    payload["stream"] = stream
    return payload


def mode_label(stream: bool) -> str:
    return "stream=true" if stream else "stream=false"


def should_run(test_name: str) -> bool:
    return not TEST_PREFIXES or any(test_name.startswith(p) for p in TEST_PREFIXES)


def should_run_any(test_names: list[str]) -> bool:
    return any(should_run(name) for name in test_names)


def test_text(model: str, stream: bool):  # type: ignore
    payload = {"model": model, "messages": [{"role": "user", "content": "こんにちは"}]}
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]["content"]
    print_result(
        f"{model}: text ({mode_label(stream)})",
        "こんにちは！何かお手伝いできることはありますか？",  # noqa: RUF001
        output,
        dt,
    )


def test_max_completion_tokens(model: str, stream: bool):  # type: ignore
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "python について説明してください。"}],
        "max_completion_tokens": 50,
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]["content"]
    print_result(
        f"{model}: max_completion_tokens=50 ({mode_label(stream)})",
        "Python（パイソン）は、世界で最も人気のある... \n(以下途切れる)",  # noqa: RUF001
        output,
        dt,
    )


def test_tool_call(model: str, stream: bool):  # type: ignore
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "東京と大阪の天気は?タイマーを30秒にセットして。",
            }
        ],
        "tools": [TOOL_WEATHER, TOOL_TIMER],
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"].get("tool_calls")
    print_result(
        f"{model}: tool_call ({mode_label(stream)})",
        '[\n  { "function": { "name": "get_weather", "arguments": "{...東京...}" } },\n  { "function": { "name": "get_weather", "arguments": "{...大阪...}" } },\n  { "function": { "name": "set_timer", "arguments": "{...30...}" } }\n]',
        output,
        dt,
    )


def test_tool_choice_auto(model: str, stream: bool):  # type: ignore
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "こんにちは"}],
        "tools": [TOOL_WEATHER, TOOL_TIMER],
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]
    print_result(
        f"{model}: tool_choice auto ({mode_label(stream)})",
        '{\n  "role": "assistant",\n  "content": "こんにちは！今日はどんなお手伝いが必要ですか？"\n}',  # noqa: RUF001
        output,
        dt,
    )


def test_tool_choice_any(model: str, stream: bool):  # type: ignore
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "こんにちは"}],
        "tools": [TOOL_WEATHER, TOOL_TIMER],
        "tool_choice": "any",
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]
    print_result(
        f"{model}: tool_choice any ({mode_label(stream)})",
        '{\n  "role": "assistant",\n  "content": null,\n  "tool_calls": [ ... ]\n}',
        output,
        dt,
    )


def test_tool_choice_specific(model: str, stream: bool):  # type: ignore
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "こんにちは"}],
        "tools": [TOOL_WEATHER, TOOL_TIMER],
        "tool_choice": {"type": "function", "function": {"name": "get_weather"}},
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]
    print_result(
        f"{model}: tool_choice specific (get_weather) ({mode_label(stream)})",
        '{\n  "role": "assistant",\n  "content": null,\n  "tool_calls": [ { "function": { "name": "get_weather" ... } } ]\n}',
        output,
        dt,
    )


def test_parallel_tool_calls_false(model: str, stream: bool):  # type: ignore
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "東京と大阪の天気は?"}],
        "tools": [TOOL_WEATHER],
        "parallel_tool_calls": False,
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]
    print_result(
        f"{model}: parallel_tool_calls=false ({mode_label(stream)})",
        '{\n  "role": "assistant",\n  "content": null,\n  "tool_calls": [ { "function": { "name": "get_weather", "arguments": "{...東京...}" } } ]\n}',
        output,
        dt,
    )


def test_continuation(model: str, stream: bool):  # type: ignore
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "語尾に「にゃ」をつけて答えてください"},
            {"role": "user", "content": "こんにちは"},
            {
                "role": "assistant",
                "content": "こんにちはにゃ！何かお手伝いできることはありますかにゃ？",  # noqa: RUF001
            },
            {"role": "user", "content": "今日の天気は？"},  # noqa: RUF001
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location": "Tokyo"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": "東京の天気は晴れ、最高気温25度、最低気温15度です。",
            },
        ],
        "tools": [TOOL_WEATHER],
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]
    print_result(
        f"{model}: continuation ({mode_label(stream)})",
        '{\n  "role": "assistant",\n  "content": "東京の天気は晴れ、最高気温25度、最低気温15度ですにゃ！"\n}',  # noqa: RUF001
        output,
        dt,
    )


def test_image(model: str, stream: bool):  # type: ignore
    img_b64 = get_base64("miineko.png")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    },
                    {"type": "text", "text": "この画像を一言で説明して"},
                ],
            }
        ],
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]["content"]
    print_result(
        f"{model}: image ({mode_label(stream)})",
        "「ピクセルアートで描かれたピンクの猫の顔」",
        output,
        dt,
    )


# --- OMNI ONLY Tests ---


def test_audio(model: str, stream: bool):  # type: ignore
    audio_b64 = get_base64("song.wav")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": audio_b64, "format": "wav"},
                    },
                    {
                        "type": "text",
                        "text": "この audio の歌詞を短く引用してください。また、この音楽の雰囲気や構成も1文で説明してください。",
                    },
                ],
            }
        ],
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]["content"]
    print_result(
        f"{model}: audio ({mode_label(stream)})",
        "**歌詞の引用:**\n「加速する世界の片端から君の声が聞こえてくる。揺れる心抱えながら、一歩ずつ前を向いて…」\n\n**雰囲気・構成の説明:**\n電子音と力強いシンセポップのギターが交錯し、情熱的で懐かしさを感じさせるメロディーが特徴的な楽曲です。",
        output,
        dt,
    )


def test_video_only(model: str, stream: bool):  # type: ignore
    video_b64 = get_base64("pv.mp4")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {"url": f"data:video/mp4;base64,{video_b64}"},
                    },
                    {
                        "type": "text",
                        "text": "この video の映像の展開を一文で説明してください。",
                    },
                ],
            }
        ],
        "use_audio_in_video": False,
        "max_completion_tokens": 6000,
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]["content"]
    print_result(
        f"{model}: video_only (use_audio_in_video=false) ({mode_label(stream)})",
        "ピンクのピクセルアートのクマが草原の小道を歩き、川を渡って村に到着しました。",
        output,
        dt,
    )


def test_video_with_audio(model: str, stream: bool):  # type: ignore
    video_b64 = get_base64("pv.mp4")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {"url": f"data:video/mp4;base64,{video_b64}"},
                    },
                    {
                        "type": "text",
                        "text": "この video の音声には歌がありますか？ある場合は聞き取れる歌詞の一部を短く引用し、映像の展開も一文で説明してください。",  # noqa: RUF001
                    },
                ],
            }
        ],
        "max_completion_tokens": 6000,
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]["content"]
    print_result(
        f"{model}: video_with_audio ({mode_label(stream)})",
        "はい、歌があります。\n\n**聞き取れる歌詞の一部**:\n加速する世界の中から\n君の声が聞こえてくる\n揺れる心を抱えながら\n一歩ずつ前を向いて\n\n**映像の展開**:\nピクセルアートのピンクのクマが画面を下から登場し、カメラが後退して広大な色鮮やかな村の風景を捉えます。",
        output,
        dt,
    )


def test_video_not_use_audio_plus_audio(model: str, stream: bool):  # type: ignore
    video_b64 = get_base64("pv.mp4")
    audio_b64 = get_base64("song.wav")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {"url": f"data:video/mp4;base64,{video_b64}"},
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {"data": audio_b64, "format": "wav"},
                    },
                    {
                        "type": "text",
                        "text": "audio から聞き取れる歌詞の一部を短く引用してください。また、video の映像の展開も一文で説明してください。",
                    },
                ],
            }
        ],
        "use_audio_in_video": False,
        "max_completion_tokens": 6000,
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]["content"]
    print_result(
        f"{model}: video (use_audio=false) + audio ({mode_label(stream)})",
        "**歌詞の一部の短く引用:**\n「加速する世界の中で\n君の声が聞こえてくる\n揺れる心抱えながら\n一歩ずつ前を向いて」\n\n**video の映像の展開:**\nアニメのキャラクターが、暖かみのある居酒屋で複数のビールを前に楽しそうに笑いながら手を振るシーン。",
        output,
        dt,
    )


def test_video_image(model: str, stream: bool):  # type: ignore
    video_b64 = get_base64("pv.mp4")
    frames = get_frames()
    if not frames:
        print(f"\n[SKIP] {model}: video_image (no frames found in assets/pv_frames)")
        return

    content = [
        {"type": "text", "text": "まず動画と音声です。"},
        {
            "type": "video_url",
            "video_url": {"url": f"data:video/mp4;base64,{video_b64}"},
        },
        {
            "type": "text",
            "text": "次に、同じ動画から1秒間隔で抜き出した秒数ラベル付きフレームです。",
        },
    ]
    # 全フレームを展開して追加
    for frame_parts in frames:
        content.extend(frame_parts)

    content.append(
        {
            "type": "text",
            "text": "この video の歌詞の一部を短く引用してください。次に、最も印象的・象徴的な瞬間の秒数(t=◯秒)を1つ選んで、その理由を1文で説明してください。",
        }
    )

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_completion_tokens": 6000,
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]["content"]
    print_result(
        f"{model}: video_image ({mode_label(stream)})",
        "詞（一部）: 「加速する世界の中から君の声が聞こえてくる」\n\n最も印象的で象徴的な瞬間: t=12秒\n\n説明: 一匹の小さなトカゲが登場し、物語の始まりや新たな道のりを象徴している。",  # noqa: RUF001
        output,
        dt,
    )


def test_video_image_tools(model: str, stream: bool):  # type: ignore
    video_b64 = get_base64("pv.mp4")
    frames = get_frames()
    if not frames:
        print(
            f"\n[SKIP] {model}: video_image_tools (no frames found in assets/pv_frames)"
        )
        return

    content = [
        {"type": "text", "text": "まず動画と音声です。"},
        {
            "type": "video_url",
            "video_url": {"url": f"data:video/mp4;base64,{video_b64}"},
        },
        {
            "type": "text",
            "text": "次に、同じ動画から1秒間隔で抜き出した秒数ラベル付きフレームです。",
        },
    ]
    for frame_parts in frames:
        content.extend(frame_parts)

    content.append(
        {
            "type": "text",
            "text": "映像・楽曲・フレームを分析し、最も印象的・象徴的な瞬間を一つ選んでください。選んだら、その秒数と、その理由を、1文で説明してください。",
        }
    )

    payload = {
        "model": model,
        "tools": [TOOL_HIGHLIGHT],
        "tool_choice": {"type": "function", "function": {"name": "record_highlight"}},
        "messages": [{"role": "user", "content": content}],
        "max_completion_tokens": 6000,
    }
    resp, dt = post_chat(with_stream(payload, stream))
    output = resp["choices"][0]["message"]
    print_result(
        f"{model}: video_image_tools ({mode_label(stream)})",
        '{\n  "role": "assistant",\n  "content": null,\n  "tool_calls": [\n    {\n      "id": "call_...",\n      "type": "function",\n      "function": {\n        "name": "record_highlight",\n        "arguments": "{\\"timestamp_seconds\\": 3, \\"reason\\": \\"...\\"}"\n      }\n    }\n  ]\n}',
        output,
        dt,
    )


# --- Main ---


def main():  # type: ignore
    print("Starting verification...")
    print(f"BASE_URL: {BASE_URL}")
    print(f"ASSETS:   {ASSETS}")
    if TEST_PREFIXES:
        print(f"FILTERS:  {', '.join(TEST_PREFIXES)}")

    ran = 0

    def run_case(name: str, fn, model: str, stream: bool) -> None:  # type: ignore
        nonlocal ran
        if not should_run(name):
            return
        fn(model, stream)
        ran += 1
        if "--fast" in sys.argv:
            print("\n[FAST MODE] Exiting early.")
            sys.exit(0)

    models_common = ["qwen3.6-27b", "qwen3-omni"]
    common_cases = [
        ("text", test_text),
        ("max_completion_tokens", test_max_completion_tokens),
        ("tool_call", test_tool_call),
        ("tool_choice_auto", test_tool_choice_auto),
        ("tool_choice_any", test_tool_choice_any),
        ("tool_choice_specific", test_tool_choice_specific),
        ("parallel_tool_calls_false", test_parallel_tool_calls_false),
        ("continuation", test_continuation),
        ("image", test_image),
    ]
    for model in models_common:
        for stream in STREAM_MODES:
            if not should_run_any([name for name, _fn in common_cases]):
                continue
            print(
                "\n\n######################################################################"
            )
            print(f"### Testing Model: {model} ({mode_label(stream)})")
            print(
                "######################################################################"
            )
            for name, fn in common_cases:
                run_case(name, fn, model, stream)

    omni = "qwen3-omni"
    omni_cases = [
        ("audio", test_audio),
        ("video_only", test_video_only),
        ("video_with_audio", test_video_with_audio),
        ("video_not_use_audio_plus_audio", test_video_not_use_audio_plus_audio),
        ("video_image", test_video_image),
        ("video_image_tools", test_video_image_tools),
    ]
    for stream in STREAM_MODES:
        if not should_run_any([name for name, _fn in omni_cases]):
            continue
        print(
            "\n\n######################################################################"
        )
        print(
            f"### Testing Model: {omni} (Audio / Video Extensions, {mode_label(stream)})"
        )
        print("######################################################################")
        for name, fn in omni_cases:
            run_case(name, fn, omni, stream)

    if ran == 0:
        print(f"\nNo tests matched prefixes: {', '.join(TEST_PREFIXES)}")
        sys.exit(2)
    print("\nAll tests completed.")


if __name__ == "__main__":
    main()
