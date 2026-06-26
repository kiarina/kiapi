from typing import Any

from pydantic import BaseModel, create_model

from kiapi.core.job import Job

from .._views.async_job_response import AsyncJobResponse


def build_job_responses(
    *media_types: str,
    result_model: type[BaseModel] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI response docs for sync/async generation endpoints.

    ``mode=async`` returns 202 with a lightweight job handle. ``mode=sync``
    returns a full Job JSON when the client asks for JSON, and may return a raw
    artifact when the endpoint produces exactly one artifact and the client did
    not request JSON.

    ``result_model`` lets a family document the capability-specific shape of
    ``Job.result`` (otherwise a free-form object): pass the family's result view
    and the 200 JSON schema becomes a Job whose ``result`` is that typed model.
    """

    job_model: type[BaseModel] = Job
    if result_model is not None:
        job_model = create_model(
            f"Job{result_model.__name__}",
            __base__=Job,
            result=(result_model | None, None),
        )

    # Pass the models via FastAPI's ``model`` key (not inline ``schema``) so
    # FastAPI hoists their definitions into ``#/components/schemas`` and rewrites
    # refs accordingly. Inlining ``model_json_schema()`` here would leave local
    # ``#/$defs`` refs that don't resolve at the OpenAPI document root (ReDoc
    # raises "Invalid reference token: $defs").
    binary_content: dict[str, Any] = {
        media_type: {"schema": {"type": "string", "format": "binary"}}
        for media_type in media_types
    }

    return {
        200: {
            "model": job_model,
            "description": (
                "Sync result. Returns Job JSON with Accept: application/json; "
                "single-artifact jobs may return raw bytes otherwise."
            ),
            "content": binary_content,
            "headers": {
                "X-Kiapi-File-Id": {
                    "description": "Produced artifact file_id when raw bytes are returned.",
                    "schema": {"type": "string"},
                },
                "X-Kiapi-Job-Id": {
                    "description": "Job id when raw bytes are returned.",
                    "schema": {"type": "string"},
                },
            },
        },
        202: {
            "model": AsyncJobResponse,
            "description": "Async job accepted. Poll GET /v1/jobs/{job_id}.",
        },
        400: {
            "description": "Invalid request for the selected model or file reference."
        },
        422: {"description": "Request schema or validation error."},
        503: {"description": "Model setup or memory budget error."},
        504: {"description": "Sync request exceeded the configured timeout."},
    }
