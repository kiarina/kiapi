"""Shape chat completions output as Responses API objects and stream events.

``completion_to_response`` converts a finished ``chat.completion``.
``ResponsesStream`` turns ``chat.completion.chunk`` dicts into Responses API
stream events: a ``message`` item for text, then one ``function_call`` item per
tool call, closed with ``response.completed`` once the job's usage is known.
"""

import time
import uuid
from typing import Any

from .._views.responses_request import ResponsesRequest


def completion_to_response(
    completion: dict[str, Any], req: ResponsesRequest
) -> dict[str, Any]:
    choice = completion["choices"][0]
    message = choice["message"]
    output: list[dict[str, Any]] = []
    if message.get("content"):
        output.append(_message_item(_new_id("msg"), message["content"]))
    for call in message.get("tool_calls") or []:
        output.append(
            _function_call_item(
                _new_id("fc"),
                call["id"],
                call["function"]["name"],
                call["function"]["arguments"],
            )
        )
    return _response(
        _new_id("resp"),
        req,
        status=_status(choice.get("finish_reason")),
        output=output,
        usage=completion.get("usage"),
    )


class ResponsesStream:
    def __init__(self, req: ResponsesRequest) -> None:
        self.req = req
        self.id = _new_id("resp")
        self.created_at = int(time.time())
        self.output: list[dict[str, Any]] = []
        self.finish_reason: str | None = None
        self._seq = 0
        self._started = False
        self._message: dict[str, Any] | None = None
        self._text = ""
        self._calls: dict[int, dict[str, Any]] = {}

    def start(self) -> list[dict[str, Any]]:
        if self._started:
            return []
        self._started = True
        snapshot = self._snapshot("in_progress")
        return [
            self._event("response.created", response=snapshot),
            self._event("response.in_progress", response=snapshot),
        ]

    def feed(self, chunk: dict[str, Any]) -> list[dict[str, Any]]:
        events = self.start()
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or {}
            if delta.get("content"):
                events += self._text_delta(delta["content"])
            for call in delta.get("tool_calls") or []:
                events += self._tool_call_delta(call)
            if choice.get("finish_reason"):
                self.finish_reason = choice["finish_reason"]
                events += self._close_message()
        return events

    def complete(self, usage: dict[str, Any] | None) -> list[dict[str, Any]]:
        events = self.start() + self._close_message()
        status = _status(self.finish_reason)
        name = "response.completed" if status == "completed" else "response.incomplete"
        events.append(self._event(name, response=self._snapshot(status, usage)))
        return events

    def fail(self, exc: BaseException) -> list[dict[str, Any]]:
        events = self.start()
        response = self._snapshot("failed")
        response["error"] = {"code": "server_error", "message": str(exc)}
        events.append(self._event("response.failed", response=response))
        return events

    # --------------------------------------------------
    # text
    # --------------------------------------------------

    def _text_delta(self, text: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        if self._message is None:
            self._message = {
                "type": "message",
                "id": _new_id("msg"),
                "status": "in_progress",
                "role": "assistant",
                "content": [],
            }
            self._text = ""
            events.append(
                self._event(
                    "response.output_item.added",
                    output_index=len(self.output),
                    item=dict(self._message),
                )
            )
            events.append(
                self._event(
                    "response.content_part.added",
                    item_id=self._message["id"],
                    output_index=len(self.output),
                    content_index=0,
                    part={"type": "output_text", "text": "", "annotations": []},
                )
            )
        self._text += text
        events.append(
            self._event(
                "response.output_text.delta",
                item_id=self._message["id"],
                output_index=len(self.output),
                content_index=0,
                delta=text,
            )
        )
        return events

    def _close_message(self) -> list[dict[str, Any]]:
        if self._message is None:
            return []
        item = _message_item(self._message["id"], self._text)
        part = item["content"][0]
        index = len(self.output)
        events = [
            self._event(
                "response.output_text.done",
                item_id=item["id"],
                output_index=index,
                content_index=0,
                text=self._text,
            ),
            self._event(
                "response.content_part.done",
                item_id=item["id"],
                output_index=index,
                content_index=0,
                part=part,
            ),
            self._event("response.output_item.done", output_index=index, item=item),
        ]
        self.output.append(item)
        self._message = None
        return events

    # --------------------------------------------------
    # function calls
    # --------------------------------------------------

    def _tool_call_delta(self, call: dict[str, Any]) -> list[dict[str, Any]]:
        events = self._close_message()
        index = call.get("index", 0)
        function = call.get("function") or {}
        state = self._calls.get(index)
        if state is None:
            item = _function_call_item(
                _new_id("fc"),
                call.get("id") or _new_id("call"),
                function.get("name", ""),
                "",
            )
            item["status"] = "in_progress"
            state = {"item": item, "output_index": len(self.output)}
            self._calls[index] = state
            self.output.append(item)
            events.append(
                self._event(
                    "response.output_item.added",
                    output_index=state["output_index"],
                    item=dict(item),
                )
            )
        item = state["item"]
        if function.get("name") and not item["name"]:
            item["name"] = function["name"]
        # Chat chunks carry each call's arguments complete, in one delta.
        if "arguments" in function:
            item["arguments"] = function["arguments"]
            item["status"] = "completed"
            events += [
                self._event(
                    "response.function_call_arguments.delta",
                    item_id=item["id"],
                    output_index=state["output_index"],
                    delta=item["arguments"],
                ),
                self._event(
                    "response.function_call_arguments.done",
                    item_id=item["id"],
                    output_index=state["output_index"],
                    arguments=item["arguments"],
                ),
                self._event(
                    "response.output_item.done",
                    output_index=state["output_index"],
                    item=dict(item),
                ),
            ]
        return events

    # --------------------------------------------------
    # shared
    # --------------------------------------------------

    def _event(self, type_: str, **fields: Any) -> dict[str, Any]:
        self._seq += 1
        return {"type": type_, "sequence_number": self._seq, **fields}

    def _snapshot(
        self, status: str, usage: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        output = [item for item in self.output if item.get("status") != "in_progress"]
        response = _response(
            self.id, self.req, status=status, output=output, usage=usage
        )
        response["created_at"] = self.created_at
        return response


def _response(
    response_id: str,
    req: ResponsesRequest,
    *,
    status: str,
    output: list[dict[str, Any]],
    usage: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "id": response_id,
        "object": "response",
        "created_at": int(time.time()),
        "status": status,
        "error": None,
        "incomplete_details": (
            {"reason": "max_output_tokens"} if status == "incomplete" else None
        ),
        "instructions": req.instructions,
        "model": req.model,
        "output": output,
        "parallel_tool_calls": req.parallel_tool_calls,
        "tool_choice": req.tool_choice if req.tool_choice is not None else "auto",
        "tools": req.tools or [],
        "store": False,
        "usage": _usage(usage) if usage is not None else None,
    }


def _status(finish_reason: str | None) -> str:
    return "incomplete" if finish_reason == "length" else "completed"


def _usage(usage: dict[str, Any]) -> dict[str, Any]:
    details = usage.get("prompt_tokens_details") or {}
    return {
        "input_tokens": usage.get("prompt_tokens", 0),
        "input_tokens_details": {"cached_tokens": details.get("cached_tokens", 0)},
        "output_tokens": usage.get("completion_tokens", 0),
        "output_tokens_details": {"reasoning_tokens": 0},
        "total_tokens": usage.get("total_tokens", 0),
    }


def _message_item(item_id: str, text: str) -> dict[str, Any]:
    return {
        "type": "message",
        "id": item_id,
        "status": "completed",
        "role": "assistant",
        "content": [{"type": "output_text", "text": text, "annotations": []}],
    }


def _function_call_item(
    item_id: str, call_id: str, name: str, arguments: str
) -> dict[str, Any]:
    return {
        "type": "function_call",
        "id": item_id,
        "call_id": call_id,
        "name": name,
        "arguments": arguments,
        "status": "completed",
    }


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"
