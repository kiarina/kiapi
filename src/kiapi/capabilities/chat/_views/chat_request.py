"""OpenAI-compatible chat request model.

``messages`` / ``tools`` are kept as loose dicts on purpose: OpenAI's multimodal
``content`` parts vary by client and we parse them leniently in
``_operations/parse_messages``. Unknown top-level fields are tolerated
(``extra="allow"``). ``model`` selects which registered chat model answers
(see core/model).
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "model": "qwen3-omni",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "What is in this image?"},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": "https://example.com/cat.png"},
                                },
                            ],
                        },
                    ],
                }
            ]
        },
    )

    messages: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        description=(
            "OpenAI-style conversation turns. Each item is "
            "`{role, content}` where `role` is `system` / `user` / "
            "`assistant` / `tool`. `content` is either a plain string or a "
            "list of typed parts for multimodal input: `{type: 'text', text}`, "
            "`{type: 'image_url', image_url: {url}}`, "
            "`{type: 'audio_url', audio_url: {url}}`, "
            "`{type: 'video_url', video_url: {url}}`, or inline base64 via "
            "`{type: 'input_audio', input_audio: {data, format}}`. A media `url` "
            "accepts an http(s) URL or a `data:` URL; `input_audio.data` is bare "
            "base64. Which modalities are accepted depends on the resolved model "
            "(see GET /v1/models)."
        ),
    )
    model: str | None = Field(
        default=None,
        description=(
            "Registered chat model name, alias, or repo id. When omitted, the "
            "family default chat model answers. See GET /v1/models for the "
            "servable list and each model's accepted input modalities."
        ),
        examples=["qwen3-omni"],
    )
    tools: list[dict[str, Any]] | None = Field(
        default=None,
        description=(
            "OpenAI function-tool definitions: "
            "`{type: 'function', function: {name, description, parameters}}` "
            "where `parameters` is a JSON Schema object. Tool calls are parsed "
            "from the model output and returned as `message.tool_calls`."
        ),
    )
    tool_choice: Any | None = Field(
        default=None,
        description=(
            "How the model may call tools: `'auto'` (default when tools are "
            "given — model decides), `'none'` (never call a tool), "
            "`'required'`/`'any'` (must call at least one tool), or a specific "
            "tool `{type: 'function', function: {name}}`."
        ),
    )
    parallel_tool_calls: bool = Field(
        default=True,
        description=(
            "OpenAI-compatible. When false, at most one tool call is returned "
            "even if the model emits several."
        ),
    )

    max_completion_tokens: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Upper bound on generated tokens. Replaces the deprecated "
            "`max_tokens`, which is rejected."
        ),
    )
    temperature: float | None = Field(
        default=None,
        description="Sampling temperature. Higher is more random; 0 is greedy.",
    )
    top_p: float | None = Field(
        default=None,
        description="Nucleus sampling cutoff in (0, 1].",
    )
    seed: int | None = Field(
        default=None,
        description="Seed for reproducible sampling when set.",
    )

    # Extensions (not in the OpenAI spec):
    fps: float | None = Field(
        default=None,
        description=(
            "kiapi extension (non-OpenAI). Frame sampling rate for video "
            "inputs, in frames per second."
        ),
    )
    use_audio_in_video: bool | None = Field(
        default=None,
        description=(
            "kiapi extension (non-OpenAI). Demux a video's audio track and feed "
            "it as audio alongside the frames. Overrides the server default."
        ),
    )
    chat_template_kwargs: dict[str, Any] | None = Field(
        default=None,
        description=(
            "kiapi extension (non-OpenAI). Extra kwargs forwarded verbatim to "
            "the tokenizer's `apply_chat_template`, e.g. "
            "`{'enable_thinking': false}` to turn off Qwen3.6's reasoning. "
            "Mirrors the vLLM/SGLang "
            "`extra_body={'chat_template_kwargs': {...}}` convention."
        ),
    )

    stream: bool = Field(
        default=False,
        description=(
            "When true, stream the answer as OpenAI-style "
            "`text/event-stream` `chat.completion.chunk` events ending with "
            "`data: [DONE]`. When false, wait for and return the full "
            "`chat.completion` object."
        ),
    )

    @model_validator(mode="after")
    def reject_deprecated_max_tokens(self):  # type: ignore
        if self.model_extra and "max_tokens" in self.model_extra:
            raise ValueError("max_tokens is deprecated; use max_completion_tokens")
        return self
