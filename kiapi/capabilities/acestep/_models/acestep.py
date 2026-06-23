"""Handler for ace-step presets (xl-base / turbo) via an isolated subprocess.

Each preset is a resident spec whose ``payload`` is an :class:`AceStepEngine` - a
long-lived ace-step worker subprocess holding the shared LLM + that preset's DiT.
``load`` spawns it (paying the model-load cost once), ``release`` terminates it
(freeing memory on eviction / TTL / shutdown), and ``generate_track`` runs one
generation over the protocol and stores the produced WAV in the global file
store. The memory manager treats the subprocess's footprint via the registry
``weight_gb`` estimate (a child process's RSS isn't visible in kiapi's own).
"""

import logging
import time
from pathlib import Path
from typing import Any

import psutil  # type: ignore

from kiapi.core.file import FileStore
from kiapi.core.job import ProgressReporter
from kiapi.core.model import ModelSpec
from kiapi.core.workdir import create_work_dir

from .._operations.resolve_ace_step_paths import resolve_ace_step_paths
from .._services.ace_step_engine import AceStepEngine
from .._settings import settings_manager
from .._views.track_params import TrackParams

FEATURES = {"text", "audio"}
logger = logging.getLogger(__name__)


def load(spec: ModelSpec) -> AceStepEngine:
    s = settings_manager.get_settings()
    paths = resolve_ace_step_paths(s)
    Path(paths.project_root).mkdir(parents=True, exist_ok=True)
    engine = AceStepEngine.spawn(
        python_path=paths.python_path,
        preset_name=spec.name,
        project_root=paths.project_root,
        checkpoint_dir=paths.checkpoint_dir,
        llm_model=s.llm_model,
        ready_timeout_s=s.ready_timeout_s,
    )
    # The child's memory isn't in kiapi's RSS; log it so the registry estimate
    # (weight_gb) can be tuned to the real footprint.
    try:
        rss_gb = psutil.Process(engine.proc.pid).memory_info().rss / (1024**3)
        logger.info(
            "%s subprocess ready - child RSS ~%.1f GB (registry estimate %.1f)",
            spec.name,
            rss_gb,
            spec.weight_gb,
        )
    except Exception:
        pass
    return engine


def release(payload: AceStepEngine) -> None:
    payload.release()


def warmup(payload: AceStepEngine) -> None:
    """No-op: spawning already loaded the LLM + DiT weights. A real generation
    would cost ~25 s, which warmup shouldn't pay."""


def generate_track(
    payload: AceStepEngine,
    params: TrackParams,
    files: FileStore,
) -> dict[str, Any]:
    """Run one generation over the subprocess, store the WAV, return metadata."""
    s = settings_manager.get_settings()
    save_dir = create_work_dir("audio/acestep")
    t0 = time.time()
    engine_params = params.engine_params()
    # generate_track runs on the single worker thread, so the job's ambient
    # ProgressReporter is bound here; ace-step's native milestones (forwarded over
    # the subprocess protocol) push straight onto the job (no-op when unbound).
    reporter = ProgressReporter.current()
    audio_path = payload.generate(
        params.task,
        engine_params,
        str(save_dir),
        timeout_s=s.job_timeout_s,
        on_progress=reporter.update,
    )
    total_s = round(time.time() - t0, 2)

    meta = {
        "task": params.task,
        "params": engine_params,
        "timings": {"total_s": total_s},
        **params.meta_extra(),
    }
    rec = files.put_path(
        audio_path,
        filename=Path(audio_path).name,
        content_type="audio/wav",
        meta=meta,
        move=True,
    )
    return {"file_id": rec.file_id, "audio_bytes": rec.size, **meta}
