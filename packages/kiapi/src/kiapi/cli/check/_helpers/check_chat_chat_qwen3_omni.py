from kiapi.capabilities.chat import ChatRequest, handle_chat
from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    result, artifacts = handle_chat(
        ctx,
        ChatRequest(
            model=spec.name,
            messages=[{"role": "user", "content": "Reply with only: ok"}],
            max_completion_tokens=4,
            temperature=0.0,
        ),
    )
    return build_check_result(spec, result, artifacts)
