"""Handler for Qwen3.6-27B (``model_type: qwen3_5``, ``Qwen3_5ForConditionalGeneration``).

A text + image vision-language model (the config also defines video tokens; we
keep v1 to image and can add video later). No audio. Owns its own generate flow;
shares the media / template / response operations with the Omni handler.

Everything Qwen3.6-specific lives here, kept private to this module:

  - the **Hermes/XML** tool-call *prefill* in :func:`_build_prompt` (how a Hermes
    call is requested; Qwen3.6 emits
    ``<tool_call><function=NAME><parameter=p>v</parameter></function></tool_call>``,
    not the JSON style Qwen3-Omni uses). The parse itself is a shared operation
    (``parse_hermes_tool_calls``).
  - the ``enable_thinking=False`` default applied to ``chat_template_kwargs``.

Notes vs. qwen3_omni:
  - No audio path → no ``load_audio`` array workaround.
  - The chunked-prefill / RoPE bug that once forced ``prefill_step_size=None`` on
    Omni was fixed upstream in mlx-vlm 0.6.3 (``get_rope_index`` rewrite) and the
    Omni workaround removed; qwen3_5 likewise runs with the default. See the
    "mlx-vlm dependency notes" section of this capability's README.
"""

import shutil
import time
from types import SimpleNamespace
from typing import Any

from kiapi.core.model import ModelSpec
from kiapi.core.workdir import create_work_dir

from .._operations.apply_template import apply_template
from .._operations.completed_hermes_tool_call_text import (
    completed_hermes_tool_call_text,
)
from .._operations.emit_streaming_response import emit_streaming_response
from .._operations.ensure_streaming_detokenizer_compat import (
    ensure_streaming_detokenizer_compat,
)
from .._operations.format_response import format_response
from .._operations.parse_hermes_tool_calls import parse_hermes_tool_calls
from .._operations.parse_messages import parse_messages
from .._operations.stream_text_from_tokens import stream_text_from_tokens
from .._utils.apply_parallel_tool_call_policy import apply_parallel_tool_call_policy
from .._utils.apply_seed import apply_seed
from .._utils.load_mlx_vlm import load_mlx_vlm
from .._utils.warmup_params import warmup_params
from .._views.chat_params import ChatParams

FEATURES = {"text", "image", "tools"}


def load(spec: ModelSpec) -> SimpleNamespace:
    return load_mlx_vlm(spec)


def warmup(payload: SimpleNamespace) -> None:
    run(payload, warmup_params("qwen3.6-27b"))


def run(  # type: ignore
    payload: SimpleNamespace,
    params: ChatParams,
    emit=None,
) -> dict[str, Any]:
    from mlx_vlm import generate, stream_generate  # type: ignore

    model, processor = payload.model, payload.processor
    tmp_dir = create_work_dir("chat/qwen3_5")
    try:
        template_messages, image_paths, _audio, _video = parse_messages(
            params.messages, tmp_dir, allow=FEATURES
        )

        # Qwen3.6 emits Hermes/XML tool calls (not JSON) — use that format's
        # prefill + parser.
        prompt, prefill = _build_prompt(
            processor,
            template_messages,
            params.tools,
            params.tool_choice,
            _chat_template_kwargs(params),
        )

        apply_seed(params.seed)
        gen_kwargs = _sampling_kwargs(params)

        if emit is not None:
            ensure_streaming_detokenizer_compat()
            buffer_for_tools = bool(
                params.tools or params.tool_choice not in (None, "none")
            )
            full, elapsed, last, tool_calls = emit_streaming_response(
                model_name=params.model,
                prefill=prefill,
                chunks=stream_text_from_tokens(
                    processor,
                    stream_generate(
                        model,
                        processor,
                        prompt,
                        image=image_paths or None,
                        **gen_kwargs,
                    ),
                ),
                emit=emit,
                parse_tool_calls=lambda full: apply_parallel_tool_call_policy(
                    parse_hermes_tool_calls(full), params.parallel_tool_calls
                ),
                buffer_for_tools=buffer_for_tools,
                completed_tool_call_text=completed_hermes_tool_call_text,
            )

            return format_response(
                model_name=params.model,
                full_text=full,
                elapsed=elapsed,
                result=last or SimpleNamespace(),
                tool_calls=tool_calls,
            )

        t0 = time.time()
        result = generate(
            model,
            processor,
            prompt,
            image=image_paths or None,
            **gen_kwargs,
        )
        elapsed = time.time() - t0

        text = getattr(result, "text", result)
        full = prefill + str(text or "")
        tool_calls = apply_parallel_tool_call_policy(
            parse_hermes_tool_calls(full), params.parallel_tool_calls
        )
        return format_response(
            model_name=params.model,
            full_text=full,
            elapsed=elapsed,
            result=result,
            tool_calls=tool_calls,  # Hermes/XML format
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _chat_template_kwargs(params: ChatParams) -> dict[str, Any]:
    kwargs = dict(params.chat_template_kwargs or {})
    kwargs.setdefault("enable_thinking", False)
    return kwargs


def _sampling_kwargs(params: ChatParams) -> dict[str, Any]:
    return {
        "max_tokens": params.max_tokens,
        "temperature": params.temperature,
        "top_p": params.top_p,
        "verbose": False,
    }


def _build_prompt(  # type: ignore
    processor,
    template_messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    tool_choice: Any,
    chat_template_kwargs: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Hermes-format prompt. Return (prompt, prefill). Implements tool_choice by prefill."""
    prompt, kind, name = apply_template(
        processor, template_messages, tools, tool_choice, chat_template_kwargs
    )

    prefill = ""
    if kind == "required":
        # Force *some* call: open the tool_call so the model emits <function=...>.
        prefill = "<tool_call>\n"
    elif kind == "function" and name:
        # Force a specific function: open the function tag; the model fills params.
        prefill = f"<tool_call>\n<function={name}>\n"

    return prompt + prefill, prefill
