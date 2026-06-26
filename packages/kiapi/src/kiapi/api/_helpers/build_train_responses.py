from typing import Any

from .._views.async_job_response import AsyncJobResponse


def build_train_responses() -> dict[int | str, dict[str, Any]]:
    return {
        # Pass the model via FastAPI's ``model`` key (not inline ``schema``) so
        # FastAPI hoists nested ``$defs`` (e.g. JobStatus) into
        # ``#/components/schemas`` and rewrites refs. Inlining
        # ``model_json_schema()`` leaves dangling ``#/$defs/...`` refs that don't
        # resolve at the document root (ReDoc raises "Invalid reference token:
        # $defs").
        202: {
            "model": AsyncJobResponse,
            "description": "Training job accepted. Poll GET /v1/jobs/{job_id}.",
        },
        400: {"description": "Invalid model or dataset FileRef."},
        422: {"description": "Request schema or validation error."},
        503: {"description": "Model setup or memory budget error."},
    }
