"""Merge a chat request with settings defaults into the complete ChatParams.

Resolves and caps the sampling knobs and fills multimodal defaults once, here,
so the per-model ``run`` works purely from :class:`ChatParams`. Model-specific
template switches (e.g. Qwen3.6's ``enable_thinking`` default) stay in the model;
this only passes ``chat_template_kwargs`` through verbatim.
"""

from .._settings import ChatSettings
from .._views.chat_params import ChatParams
from .._views.chat_request import ChatRequest


def resolve_chat_params(
    settings: ChatSettings,
    req: ChatRequest,
    *,
    variant: str,
) -> ChatParams:
    requested_max_tokens = req.max_completion_tokens
    if requested_max_tokens is None:
        requested_max_tokens = settings.default_max_tokens
    max_tokens = min(requested_max_tokens, settings.max_tokens_cap)

    temperature = (
        req.temperature if req.temperature is not None else settings.default_temperature
    )
    top_p = req.top_p if req.top_p is not None else settings.default_top_p
    fps = req.fps if req.fps is not None else settings.default_fps
    use_audio_in_video = (
        req.use_audio_in_video
        if req.use_audio_in_video is not None
        else settings.use_audio_in_video
    )

    return ChatParams(
        model=variant,
        messages=req.messages,
        tools=req.tools,
        tool_choice=req.tool_choice,
        parallel_tool_calls=req.parallel_tool_calls,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        seed=req.seed,
        fps=fps,
        use_audio_in_video=use_audio_in_video,
        chat_template_kwargs=req.chat_template_kwargs,
        stream=req.stream,
    )
