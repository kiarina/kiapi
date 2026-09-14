"""ace-step worker subprocess — runs under the ace-step venv (transformers 4.x).

kiapi's main process can't import ``acestep`` (it pins transformers 4.x, which
conflicts with chat/embedding's transformers 5.x). So ace-step
generation runs here, in a separate Python launched from the ace-step venv, and
kiapi talks to it over a tiny line-oriented JSON protocol on stdin/stdout.

This module is NEVER imported by kiapi; it is executed as a script:

    <ace-step-venv>/bin/python -m ... worker_subprocess.py \
        --preset-name xl-base --project-root <dir> \
        --checkpoint-dir <dir>/checkpoints --llm-model acestep-5Hz-lm-1.7B

Protocol (one JSON object per line):
  - stdout, on ready:           @@KIAPI@@{"event":"ready"}
  - stdin, one request/line:    {"id":"..","task":"text2music","params":{...},"save_dir":".."}
  - stdout, progress/line:      @@KIAPI@@{"id":"..","event":"progress","fraction":0.5,"label":".."}
  - stdout, one reply/line:     @@KIAPI@@{"id":"..","ok":true,"path":".."}
                            or  @@KIAPI@@{"id":"..","ok":false,"error":".."}

ace-step's ``generate_music`` takes a Gradio-style ``progress(fraction, desc=...)``
callback that fires at real milestones (LLM phases, a self-calibrating diffusion
estimator, decode, finalize). We pass one that re-emits each call as a
``progress`` protocol line tagged with the request id; the kiapi side forwards it
onto the job's :class:`ProgressReporter`. Any number of progress lines may precede
the single terminal reply for a request.

All library logging is redirected to stderr so fd 1 carries only ``@@KIAPI@@``-
prefixed protocol lines (kiapi ignores any other stdout noise defensively).
The generation logic (_build_params + presets) is ported verbatim from
ace-step-1.5-server's main.py so behavior is identical.
"""

import argparse
import json
import os
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path

# Keep fd 1 clean for the protocol: send every library print()/log to stderr.
_PROTO_OUT = sys.__stdout__
sys.stdout = sys.stderr

SENTINEL = "@@KIAPI@@"


def _emit(obj: dict) -> None:
    _PROTO_OUT.write(SENTINEL + json.dumps(obj, ensure_ascii=False) + "\n")  # type: ignore
    _PROTO_OUT.flush()  # type: ignore


def _make_progress(rid):  # type: ignore
    def _progress(value=0.0, desc=None, *args, **kwargs):  # type: ignore
        try:
            _emit(
                {
                    "id": rid,
                    "event": "progress",
                    "fraction": float(value),
                    "label": desc if isinstance(desc, str) else None,
                }
            )
        except Exception:
            pass

    return _progress


# --- model presets (ported from ace-step-1.5-server/main.py) -----------------


@dataclass
class ModelPreset:
    config_path: str
    inference_steps: int
    guidance_scale: float
    shift: float
    use_adg: bool
    dcw_enabled: bool


PRESETS: dict[str, ModelPreset] = {
    "turbo": ModelPreset(
        config_path="acestep-v15-turbo",
        inference_steps=8,
        guidance_scale=1.0,
        shift=3.0,
        use_adg=False,
        dcw_enabled=True,
    ),
    "xl-base": ModelPreset(
        config_path="acestep-v15-xl-base",
        inference_steps=32,
        guidance_scale=7.0,
        shift=3.0,
        use_adg=False,
        dcw_enabled=False,
    ),
}


def _build_params(task: str, p: dict, preset: ModelPreset):  # type: ignore
    """Map a protocol request into ace-step GenerationParams. Ported verbatim."""
    from acestep.inference import GenerationParams  # type: ignore

    common = {
        "inference_steps": p.get("inference_steps") or preset.inference_steps,
        "guidance_scale": p["guidance_scale"]
        if p.get("guidance_scale") is not None
        else preset.guidance_scale,
        "shift": p["shift"] if p.get("shift") is not None else preset.shift,
        "use_adg": preset.use_adg,
        "dcw_enabled": preset.dcw_enabled,
        "seed": p.get("seed", -1),
    }

    if task == "text2music":
        return GenerationParams(
            task_type="text2music",
            thinking=True,
            caption=p["prompt"],
            lyrics=p.get("lyrics", "[Instrumental]"),
            vocal_language=p.get("lang", "ja"),
            duration=p.get("duration", 60),
            **common,
        )
    if task == "cover":
        return GenerationParams(
            task_type="cover",
            thinking=False,
            caption=p["prompt"],
            lyrics="[Instrumental]",
            src_audio=p["src_audio"],
            audio_cover_strength=p.get("strength", 0.7),
            duration=p.get("duration"),
            **common,
        )
    if task == "repaint":
        return GenerationParams(
            task_type="repaint",
            thinking=False,
            caption=p["prompt"],
            lyrics="[Instrumental]",
            src_audio=p["src_audio"],
            repainting_start=p["start"],
            repainting_end=p.get("end", -1),
            repaint_strength=p.get("strength", 0.5),
            **common,
        )
    if task == "extract":
        return GenerationParams(
            task_type="extract",
            thinking=False,
            caption=p["target"],
            lyrics="[Instrumental]",
            src_audio=p["src_audio"],
            **common,
        )
    raise ValueError(f"unknown task: {task!r}")


# --- handlers ----------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset-name", required=True, choices=list(PRESETS))
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--checkpoint-dir", required=True)
    ap.add_argument("--llm-model", required=True)
    args = ap.parse_args()

    preset = PRESETS[args.preset_name]

    # Pin where ace-step finds the checkpoints (highest-priority lever in its
    # get_checkpoints_dir resolution), so kiapi's checkpoint_dir is authoritative
    # regardless of project_root layout. Must be set before importing acestep.
    os.environ.setdefault("ACESTEP_CHECKPOINTS_DIR", args.checkpoint_dir)

    from acestep.handler import AceStepHandler  # type: ignore
    from acestep.inference import GenerationConfig, generate_music
    from acestep.llm_inference import LLMHandler  # type: ignore

    # Load the shared LLM + this preset's DiT (mirrors the original server).
    llm = LLMHandler()
    msg, ok = llm.initialize(
        checkpoint_dir=args.checkpoint_dir,
        lm_model_path=args.llm_model,
        backend="mlx",
        device="auto",
        offload_to_cpu=False,
        dtype=None,
    )
    if not ok:
        _emit({"event": "error", "error": f"LLM init failed: {msg}"})
        sys.exit(1)

    dit = AceStepHandler()
    msg, ok = dit.initialize_service(
        project_root=args.project_root,
        config_path=preset.config_path,
        device="auto",
        offload_to_cpu=False,
    )
    if not ok:
        _emit({"event": "error", "error": f"DiT init failed: {msg}"})
        sys.exit(1)

    _emit({"event": "ready", "preset": args.preset_name})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = req.get("id")
        try:
            params = _build_params(req["task"], req["params"], preset)
            config = GenerationConfig(batch_size=1, audio_format="wav")
            result = generate_music(
                dit,
                llm,
                params=params,
                config=config,
                save_dir=req["save_dir"],
                progress=_make_progress(rid),
            )
            if not getattr(result, "success", False):
                raise RuntimeError(
                    getattr(result, "status_message", "generation failed")
                )
            path = result.audios[0].get("path", "")
            if not path or not Path(path).exists():
                raise RuntimeError("generation finished but no audio file was produced")
            _emit({"id": rid, "ok": True, "path": path})
        except Exception as exc:
            traceback.print_exc()
            _emit({"id": rid, "ok": False, "error": f"{type(exc).__name__}: {exc}"})


if __name__ == "__main__":
    main()
