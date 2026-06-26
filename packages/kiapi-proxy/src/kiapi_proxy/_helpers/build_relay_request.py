import base64
import json

from starlette.datastructures import UploadFile
from starlette.requests import Request

from kiapi_relay import RelayRequest


async def build_relay_request(request: Request) -> RelayRequest:
    """Translate an incoming HTTP request into a ``RelayRequest``.

    JSON object bodies are forwarded as ``body``; ``multipart/form-data`` uploads
    are forwarded as ``multipart`` with file bytes base64-encoded. Other content
    types are forwarded without a body (the relay only supports JSON and
    multipart payloads).
    """
    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"

    headers = dict(request.headers)
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip()
    content_type = content_type.lower()

    body: dict[str, object] | None = None
    multipart: dict[str, object] | None = None

    if content_type == "multipart/form-data":
        form = await request.form()
        try:
            fields: dict[str, str] = {}
            files: list[dict[str, object]] = []
            for key, value in form.multi_items():
                if isinstance(value, UploadFile):
                    content = await value.read()
                    files.append(
                        {
                            "field": key,
                            "filename": value.filename or "upload",
                            "content_type": value.content_type,
                            "content_base64": base64.b64encode(content).decode("ascii"),
                        }
                    )
                else:
                    fields[key] = value
        finally:
            await form.close()
        multipart = {"fields": fields, "files": files}
    elif content_type == "application/json" or content_type.endswith("+json"):
        raw = await request.body()
        if raw:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("relay only supports JSON object request bodies")
            body = data

    return RelayRequest.model_validate(
        {
            "method": request.method,
            "path": path,
            "headers": headers,
            "body": body,
            "multipart": multipart,
        }
    )
