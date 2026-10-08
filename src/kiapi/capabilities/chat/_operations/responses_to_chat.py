"""Convert a Responses API request into a chat completions request.

Leading ``system`` / ``developer`` messages (and ``instructions``) merge into one
system message, because the Qwen chat templates accept a system message only at
the start. A later ``developer`` message becomes a user message. Consecutive
``function_call`` items join the preceding assistant message as ``tool_calls``.

``namespace`` tools (Codex groups each MCP server's tools this way) flatten into
plain functions named ``<namespace>__<name>``; ``namespaced_tool_names`` maps
those names back so the output can carry ``namespace`` and ``name`` again.
"""

import json
from typing import Any

from kiapi.capabilities import ValidationError

from .._views.chat_request import ChatRequest
from .._views.responses_request import ResponsesRequest

_TEXT_PARTS = ("input_text", "output_text", "text", "summary_text")
_IGNORED_ITEMS = ("reasoning",)
_NAMESPACE_SEPARATOR = "__"


def namespaced_tool_names(req: ResponsesRequest) -> dict[str, tuple[str, str]]:
    """Flattened function name -> (namespace, name) for every namespaced tool."""
    names: dict[str, tuple[str, str]] = {}
    for tool in req.tools or []:
        if tool.get("type") == "namespace":
            for inner in tool.get("tools") or []:
                names[_joined(tool["name"], inner["name"])] = (
                    tool["name"],
                    inner["name"],
                )
    return names


def _joined(namespace: str, name: str) -> str:
    return f"{namespace}{_NAMESPACE_SEPARATOR}{name}"


def responses_to_chat(req: ResponsesRequest, *, stream: bool) -> ChatRequest:
    if req.model_extra and req.model_extra.get("previous_response_id"):
        raise ValidationError(
            "previous_response_id is not supported; send the whole conversation in input"
        )

    data: dict[str, Any] = {
        "model": req.model,
        "messages": _messages(req),
        "parallel_tool_calls": req.parallel_tool_calls,
        "stream": stream,
    }
    if req.tools:
        data["tools"] = [f for t in req.tools for f in _tools(t)]
    if req.tool_choice is not None:
        data["tool_choice"] = _tool_choice(req.tool_choice)
    if req.max_output_tokens is not None:
        data["max_completion_tokens"] = req.max_output_tokens
    for key in ("temperature", "top_p", "chat_template_kwargs"):
        value = getattr(req, key)
        if value is not None:
            data[key] = value
    return ChatRequest.model_validate(data)


def _messages(req: ResponsesRequest) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = (
        [{"type": "message", "role": "user", "content": req.input}]
        if isinstance(req.input, str)
        else req.input
    )

    system: list[str] = [req.instructions] if req.instructions else []
    messages: list[dict[str, Any]] = []
    for item in items:
        kind = item.get("type", "message")
        if kind in _IGNORED_ITEMS:
            continue
        if kind == "message":
            role = item.get("role")
            if role in ("system", "developer"):
                text = _text(item.get("content"))
                if not messages:
                    system.append(text)
                else:
                    messages.append({"role": "user", "content": text})
            elif role in ("user", "assistant"):
                messages.append(
                    {"role": role, "content": _content(item.get("content"))}
                )
            else:
                raise ValidationError(f"unsupported message role: {role!r}")
        elif kind == "function_call":
            call = {
                "id": item.get("call_id") or item.get("id"),
                "type": "function",
                "function": {
                    "name": (
                        _joined(item["namespace"], item.get("name", ""))
                        if item.get("namespace")
                        else item.get("name")
                    ),
                    "arguments": item.get("arguments") or "{}",
                },
            }
            last = messages[-1] if messages else None
            if last is not None and last["role"] == "assistant":
                last.setdefault("tool_calls", []).append(call)
            else:
                messages.append(
                    {"role": "assistant", "content": None, "tool_calls": [call]}
                )
        elif kind == "function_call_output":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item.get("call_id"),
                    "content": _output(item.get("output")),
                }
            )
        else:
            raise ValidationError(f"unsupported input item type: {kind!r}")

    if system:
        messages.insert(0, {"role": "system", "content": "\n\n".join(system)})
    if not any(m["role"] != "system" for m in messages):
        raise ValidationError("input has no user or assistant message")
    return messages


def _content(content: Any) -> str | list[dict[str, Any]]:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        raise ValidationError("message content must be a string or a list of parts")

    parts: list[dict[str, Any]] = []
    for part in content:
        kind = part.get("type")
        if kind in _TEXT_PARTS:
            parts.append({"type": "text", "text": part.get("text", "")})
        elif kind == "input_image":
            url = part.get("image_url")
            if not url:
                raise ValidationError(
                    "input_image needs image_url (file_id is not supported)"
                )
            parts.append({"type": "image_url", "image_url": {"url": url}})
        elif kind == "refusal":
            parts.append({"type": "text", "text": part.get("refusal", "")})
        else:
            raise ValidationError(f"unsupported content part type: {kind!r}")

    if all(p["type"] == "text" for p in parts):
        return "".join(p["text"] for p in parts)
    return parts


def _text(content: Any) -> str:
    value = _content(content)
    if isinstance(value, str):
        return value
    raise ValidationError("system and developer messages accept text only")


def _output(output: Any) -> str:
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        # MCP tools return several parts; images cannot go into a tool message.
        return "\n".join(
            p.get("text", "")
            if p.get("type") in _TEXT_PARTS
            else f"[{p.get('type')} omitted]"
            for p in output
        )
    return json.dumps(output, ensure_ascii=False)


def _tools(tool: dict[str, Any]) -> list[dict[str, Any]]:
    if tool.get("type") == "namespace":
        return [
            _function(inner, name=_joined(tool["name"], inner["name"]))
            for inner in tool.get("tools") or []
        ]
    return [_function(tool, name=tool.get("name"))]


def _function(tool: dict[str, Any], *, name: str | None) -> dict[str, Any]:
    if tool.get("type") != "function":
        raise ValidationError(f"unsupported tool type: {tool.get('type')!r}")
    function: dict[str, Any] = {"name": name}
    if tool.get("description"):
        function["description"] = tool["description"]
    function["parameters"] = tool.get("parameters") or {
        "type": "object",
        "properties": {},
    }
    return {"type": "function", "function": function}


def _tool_choice(choice: Any) -> Any:
    if isinstance(choice, dict) and choice.get("type") == "function":
        return {"type": "function", "function": {"name": choice.get("name")}}
    return choice
