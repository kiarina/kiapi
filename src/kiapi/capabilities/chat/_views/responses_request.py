"""OpenAI-compatible Responses API request model.

A stateless subset: the client sends the whole conversation in ``input`` every
time (``store: false``), as Codex does. ``input`` items and ``tools`` stay loose
dicts and are converted to a chat request in ``_operations/responses_to_chat``.
Unknown top-level fields are tolerated (``extra="allow"``).
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResponsesRequest(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "model": "vlm",
                    "instructions": "You are a helpful assistant.",
                    "input": "Hello!",
                }
            ]
        },
    )

    model: str = Field(
        ...,
        min_length=1,
        description="Registered chat model name, alias, or repo id (see GET /v1/models).",
        examples=["vlm"],
    )
    input: str | list[dict[str, Any]] = Field(
        ...,
        description=(
            "A user message as a string, or the whole conversation as items: "
            "`message` (`role` `user` / `assistant` / `system` / `developer`, "
            "`content` a string or `input_text` / `output_text` / `input_image` "
            "parts), `function_call`, and `function_call_output`. `reasoning` "
            "items are ignored."
        ),
    )
    instructions: str | None = Field(
        default=None,
        description="System instructions placed before the conversation.",
    )
    tools: list[dict[str, Any]] | None = Field(
        default=None,
        description=(
            "Function tools: `{type: 'function', name, description, parameters}`. "
            "Other tool types are rejected."
        ),
    )
    tool_choice: Any | None = Field(
        default=None,
        description=(
            "`'auto'`, `'none'`, `'required'`, or `{type: 'function', name}`."
        ),
    )
    parallel_tool_calls: bool = Field(
        default=True,
        description="When false, at most one function call is returned.",
    )
    max_output_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Upper bound on generated tokens.",
    )
    temperature: float | None = Field(default=None, description="Sampling temperature.")
    top_p: float | None = Field(
        default=None, description="Nucleus sampling cutoff in (0, 1]."
    )
    stream: bool = Field(
        default=False,
        description=(
            "When true, stream Responses API events (`response.created`, "
            "`response.output_item.added`, `response.output_text.delta`, ..., "
            "`response.completed`) as `text/event-stream`."
        ),
    )
    store: bool | None = Field(
        default=None,
        description=(
            "Accepted for compatibility. kiapi never stores responses, so "
            "`previous_response_id` is not supported."
        ),
    )
    chat_template_kwargs: dict[str, Any] | None = Field(
        default=None,
        description=(
            "kiapi extension (non-OpenAI). Forwarded to the chat template, as in "
            "`POST /v1/chat/completions`. The `reasoning` field is ignored."
        ),
    )
