"""Idempotently register a denoising-progress callback on an mflux model.

Called right before ``model.generate_image(...)`` in each image family's
generation helper. Every mflux model exposes ``model.callbacks`` (a
``CallbackRegistry``) and runs ``ctx.in_loop(t, latents)`` once per denoise step;
the registry routes anything with ``call_in_loop`` to the in-loop list.

The callback holds no per-job state — it reads the job's ambient
:class:`ProgressReporter` (see core/job) each step — so a single instance can stay
registered on a resident model and serve every job (silently no-op when no job is
bound). Models built via different paths (resident ``load`` vs one-off transient
builds) all funnel through here, and resident models persist across jobs, so
registration is idempotent to avoid stacking a fresh callback per call.
"""

from typing import Any

from kiapi.core.job import ProgressReporter


class _MfluxProgressCallback:
    def __init__(self, label: str = "denoising") -> None:
        self._label = label

    def call_in_loop(
        self,
        t: int,
        seed: int,
        prompt: str,
        latents: Any,
        config: Any,
        time_steps: Any,
    ) -> None:
        # ``time_steps`` is the tqdm driving the loop; ``.n`` counts steps
        # completed before this one, so ``n + 1`` are done after it.
        total = getattr(time_steps, "total", 0) or getattr(
            config, "num_inference_steps", 0
        )
        done = getattr(time_steps, "n", 0) + 1
        ProgressReporter.current().step(int(done), int(total), self._label)


def attach_mflux_progress(model: Any, *, label: str = "denoising") -> None:
    registry = getattr(model, "callbacks", None)
    if registry is None:
        return  # not an mflux model with a callback registry; nothing to do
    in_loop = getattr(registry, "in_loop", [])
    if any(isinstance(cb, _MfluxProgressCallback) for cb in in_loop):
        return  # already attached (resident model reused across jobs)
    registry.register(_MfluxProgressCallback(label=label))
