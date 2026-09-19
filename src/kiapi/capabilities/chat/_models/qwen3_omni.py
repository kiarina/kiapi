"""Handler for Qwen3-Omni (``model_type: qwen3_omni_moe``).

Owns the full generate flow for the Omni model — text + image + audio + video in,
text / tool calls out. Everything Omni-specific lives here, kept private to this
module:

  - the **JSON** tool-call *prefill* in :func:`_build_prompt` (how a JSON call is
    requested). The parse itself is shared (``parse_json_tool_calls``) because
    Qwen3.6's Hermes parser falls back to it. (Qwen3.6 uses a different, Hermes/XML
    prefill — see ``qwen3_5``.)

Other Omni-specific workarounds (distilled from the test-qwen3-omni investigation):
  (A) audio is passed as float32 arrays loaded by ``load_audio_mono``, not as
      paths: mlx-vlm's own ``load_audio`` resamples stereo along the channel
      axis (patch B in the README; upstream Blaizzy/mlx-vlm#2258).

Workaround (D) — disabling chunked prefill (``prefill_step_size=None``) on vision
prompts over 2048 tokens to dodge a ``get_rope_index`` bug — was removed after
mlx-vlm 0.6.3 rewrote ``get_rope_index``; video + many-frame prompts now run with
default chunked prefill (verified on device). See the "mlx-vlm dependency
notes" section of this capability's README.

Media placeholders (image/audio/video, and the audio demuxed from a sounded
video) are inserted in document order by ``parse_messages`` + the chat template,
so we don't hand-place them here.
"""

import inspect
import shutil
import time
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from kiapi.core.model import ModelSpec
from kiapi.core.workdir import create_work_dir

from .._operations.apply_template import apply_template
from .._operations.cancel_on_request import cancel_on_request
from .._operations.collect_generation import collect_generation
from .._operations.emit_streaming_response import emit_streaming_response
from .._operations.ensure_omni_apc_embeddings import ensure_omni_apc_embeddings
from .._operations.ensure_omni_deepstack_window import ensure_omni_deepstack_window
from .._operations.ensure_omni_image_video_join import ensure_omni_image_video_join
from .._operations.format_response import format_response
from .._operations.initialize_apc import initialize_apc
from .._operations.limit_to_context import limit_to_context
from .._operations.log_apc_result import log_apc_result
from .._operations.parse_json_tool_calls import parse_json_tool_calls
from .._operations.parse_messages import parse_messages
from .._utils.apply_parallel_tool_call_policy import apply_parallel_tool_call_policy
from .._utils.apply_seed import apply_seed
from .._utils.load_audio_mono import load_audio_mono
from .._utils.load_mlx_vlm import load_mlx_vlm
from .._utils.media_apc_tenant import media_apc_tenant
from .._utils.warmup_params import warmup_params
from .._views.chat_params import ChatParams

FEATURES = {"text", "image", "audio", "video", "tools"}
CONTEXT_WINDOW_KEYS = ("thinker_config", "text_config", "max_position_embeddings")


def load(spec: ModelSpec) -> SimpleNamespace:
    payload = load_mlx_vlm(spec)
    initialize_apc(payload)
    if payload.apc_manager is not None:
        # Media prefixes require a restorable snapshot, not independent blocks.
        payload.apc_manager._layer_major_memory_min_tokens = 1
    return payload


def release(payload: SimpleNamespace) -> None:
    if payload.apc_manager is not None:
        payload.apc_manager.clear()
        payload.apc_manager.close()


def resident_extra_bytes(payload: SimpleNamespace) -> int:
    manager = payload.apc_manager
    return manager.resident_bytes() if manager is not None else 0


def warmup(payload: SimpleNamespace) -> None:
    run(payload, warmup_params("qwen3-omni"))


def run(  # type: ignore
    payload: SimpleNamespace,
    params: ChatParams,
    emit=None,
    cancel_requested: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    from mlx_vlm import stream_generate

    ensure_omni_apc_embeddings()
    ensure_omni_image_video_join()  # needed for image + video input
    ensure_omni_deepstack_window()  # needed for long image/video prompts

    model, processor = payload.model, payload.processor
    tmp_dir = create_work_dir("chat/qwen3_omni")
    try:
        template_messages, image_paths, audio_paths, video_paths = parse_messages(
            params.messages,
            tmp_dir,
            allow=FEATURES,
            use_audio_in_video=params.use_audio_in_video,
        )

        # (A) audio as float32 arrays at the model's sampling rate. We downmix +
        # resample ourselves (load_audio_mono) because mlx-vlm's load_audio
        # mis-resamples stereo clips whose rate differs from the target.
        sr = processor.feature_extractor.sampling_rate
        audio_arrays = [load_audio_mono(p, sr=sr) for p in audio_paths]

        prompt, prefill = _build_prompt(
            processor,
            template_messages,
            params.tools,
            params.tool_choice,
            params.chat_template_kwargs,
        )

        apply_seed(params.seed)
        gen_kwargs = _sampling_kwargs(params)
        media_prefix_enabled = (
            getattr(model, "supports_media_prefix_apc", False)
            and "apc_media_prefix" in inspect.signature(stream_generate).parameters
        )
        apc_tenant = payload.apc_tenant
        if media_prefix_enabled:
            gen_kwargs["apc_media_prefix"] = True
        elif payload.apc_manager is not None:
            apc_tenant = media_apc_tenant(
                apc_tenant,
                image_paths,
                audio_paths,
                video_paths,
                fps=params.fps,
                use_audio_in_video=params.use_audio_in_video,
            )

        if video_paths:
            gen_kwargs["fps"] = params.fps

        chunks = cancel_on_request(
            limit_to_context(
                stream_generate(
                    model,
                    processor,
                    prompt,
                    image=image_paths or None,
                    audio=audio_arrays or None,  # type: ignore[arg-type]  # (A) arrays, not paths
                    video=video_paths or None,
                    apc_manager=payload.apc_manager,
                    apc_tenant=apc_tenant,
                    **gen_kwargs,
                ),
                payload.context_window,
            ),
            cancel_requested,
            payload.apc_manager.clear if payload.apc_manager is not None else None,
        )

        if emit is not None:
            buffer_for_tools = bool(
                params.tools or params.tool_choice not in (None, "none")
            )
            full, elapsed, last, tool_calls = emit_streaming_response(
                model_name=params.model,
                prefill=prefill,
                chunks=chunks,
                emit=emit,
                parse_tool_calls=lambda full: apply_parallel_tool_call_policy(
                    parse_json_tool_calls(full), params.parallel_tool_calls
                ),
                buffer_for_tools=buffer_for_tools,
                parallel_tool_calls=params.parallel_tool_calls,
            )

            log_apc_result(payload, params.model, last)
            return format_response(
                model_name=params.model,
                full_text=full,
                elapsed=elapsed,
                result=last or SimpleNamespace(),
                tool_calls=tool_calls,
            )

        t0 = time.time()
        text, last = collect_generation(processor, chunks)
        elapsed = time.time() - t0

        log_apc_result(payload, params.model, last)
        full = prefill + text
        tool_calls = apply_parallel_tool_call_policy(
            parse_json_tool_calls(full), params.parallel_tool_calls
        )
        return format_response(
            model_name=params.model,
            full_text=full,
            elapsed=elapsed,
            result=last or SimpleNamespace(),
            tool_calls=tool_calls,  # JSON format
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


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
    """JSON-format prompt. Return (prompt, prefill). Implements tool_choice by prefill."""
    prompt, kind, name = apply_template(
        processor, template_messages, tools, tool_choice, chat_template_kwargs
    )

    prefill = ""
    if kind == "required":
        prefill = "<tool_call>\n"
    elif kind == "function" and name:
        # Prefill into the *arguments object* (open brace included) so the model
        # continues inside it. Stopping at `"arguments": ` lets it emit a bare
        # scalar instead of an object under heavy multimodal load.
        prefill = f'<tool_call>\n{{"name": "{name}", "arguments": {{'

    return prompt + prefill, prefill
