from typing import Protocol

from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec

from .._schemas.check_result import CheckResult


class CheckOperation(Protocol):
    def __call__(self, ctx: AppContext, spec: ModelSpec) -> CheckResult: ...
