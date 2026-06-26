"""Chat service entry: resolve → acquire (memory budget) → run.

This is the body of the chat job's worker-thread thunk. It mirrors mlx-vlm-server's
Engine.run, but loads through the *global* memory manager so chat models share the
budget with every other capability. ``emit`` (when set) streams OpenAI-style SSE
chunks from the worker thread; the final completion dict is still returned.
"""

from kiapi.core.app import AppContext
from kiapi.core.model import model_registry

from .._settings import settings_manager
from .._views.chat_request import ChatRequest
from .resolve_chat_params import resolve_chat_params


def handle_chat(ctx: AppContext, req: ChatRequest, emit=None) -> tuple[dict, list[str]]:  # type: ignore
    """Run one chat completion. Returns (openai_completion, artifact_file_ids)."""
    settings = settings_manager.get_settings()
    spec = model_registry.resolve("chat", req.model)
    ctx.ensure_model_ready(spec)
    params = resolve_chat_params(settings, req, variant=spec.name)
    payload = ctx.memory_manager.acquire(spec)
    result = spec.module.run(payload, params, emit=emit)
    return result, []  # chat produces no file artifacts
