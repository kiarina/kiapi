"""Register a token-generation progress callback on an AudioGen model.

Called right before ``model.generate(..., progress=True)`` in the audiogen
generation helper. ``mlx_audiocraft``'s ``AudioGen`` exposes a single progress
slot via ``set_custom_progress_callback`` and invokes it once per autoregressive
decode step with ``(generated_tokens, tokens_to_generate)`` (see
``genmodel._generate_tokens`` / ``lm.generate``).

The callback holds no per-job state — it reads the job's ambient
:class:`ProgressReporter` (see core/job) each step — so a single instance can stay
registered on the resident model and serve every job (silently no-op when no job
is bound). Unlike mflux's callback registry this is a single slot, so re-setting
it on each call is naturally idempotent.
"""

from typing import Any

from kiapi.core.job import ProgressReporter


def attach_audiogen_progress(model: Any, *, label: str = "generating") -> None:
    def _callback(generated_tokens: int, tokens_to_generate: int) -> None:
        ProgressReporter.current().step(
            int(generated_tokens), int(tokens_to_generate), label
        )

    model.set_custom_progress_callback(_callback)
