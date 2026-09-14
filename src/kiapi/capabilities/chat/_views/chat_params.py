"""The complete contract for one chat completion run.

Built from settings + request by ``resolve_chat_params``; a model's ``run`` needs
nothing else (no ``req`` / ``settings``) to generate the completion. ``model`` is
the canonical model name to echo back; sampling knobs are already resolved and
capped. ``messages`` / ``tools`` / ``tool_choice`` are the request's raw OpenAI
shapes (parsed per-model via ``parse_messages`` + each model's tool format).
"""

from typing import Any

from pydantic import BaseModel


class ChatParams(BaseModel):
    model: str

    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None
    tool_choice: Any | None
    parallel_tool_calls: bool

    # Resolved + capped sampling knobs.
    max_tokens: int
    temperature: float
    top_p: float
    seed: int | None

    # Multimodal knobs (resolved defaults).
    fps: float
    use_audio_in_video: bool

    chat_template_kwargs: dict[str, Any] | None
    stream: bool
