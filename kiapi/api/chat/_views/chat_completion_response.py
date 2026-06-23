"""OpenAI-compatible ``chat.completion`` response model.

Mirrors the dict shaped by ``capabilities/chat/_operations/format_response`` so
the non-streaming response is self-describing in OpenAPI. It is an output-side
projection of the model result (not a model-coupled view), so it lives under
``api/chat/_views``. Streaming responses use a separate ``chat.completion.chunk``
shape and are documented on the endpoint.

``ChatCompletionResponse`` is the sole public element; the nested pieces are
private since nothing references them on their own.
"""

from pydantic import BaseModel, Field


class _FunctionCall(BaseModel):
    name: str = Field(description="Called function name, matching a request tool.")
    arguments: str = Field(
        description="Call arguments as a JSON-encoded string (OpenAI convention)."
    )


class _ToolCall(BaseModel):
    id: str = Field(description="Unique id for this tool call, e.g. `call_<hex>`.")
    type: str = Field(default="function", description="Always `function`.")
    function: _FunctionCall = Field(description="The function and its arguments.")


class _ResponseMessage(BaseModel):
    role: str = Field(default="assistant", description="Always `assistant`.")
    content: str | None = Field(
        default=None,
        description=(
            "Assistant text. Null when the turn is only tool calls; may hold the "
            "natural-language preamble that preceded a tool call."
        ),
    )
    tool_calls: list[_ToolCall] | None = Field(
        default=None,
        description="Tool calls the model requested, when any.",
    )


class _Choice(BaseModel):
    index: int = Field(description="Choice index (always 0; kiapi returns one).")
    message: _ResponseMessage = Field(description="The generated assistant message.")
    finish_reason: str = Field(
        description="`stop` for normal completion, `tool_calls` when tools were called."
    )


class _Usage(BaseModel):
    prompt_tokens: int = Field(description="Tokens in the prompt.")
    completion_tokens: int = Field(description="Tokens generated.")
    total_tokens: int = Field(description="Sum of prompt and completion tokens.")


class _Timings(BaseModel):
    total_s: float = Field(description="Wall-clock generation time in seconds.")


class ChatCompletionResponse(BaseModel):
    id: str = Field(description="Completion id, e.g. `chatcmpl-<hex>`.")
    object: str = Field(
        default="chat.completion", description="Always `chat.completion`."
    )
    created: int = Field(description="Unix timestamp (seconds) when created.")
    model: str = Field(description="Resolved model name that answered.")
    choices: list[_Choice] = Field(description="Generated choices (one).")
    usage: _Usage = Field(description="Token accounting for the request.")
    timings: _Timings = Field(description="kiapi extension: server-side timing.")
