"""Files API: upload / list / get / download / delete. Unified across capabilities."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from kiapi.api import REQUIRE_AUTH, get_ctx
from kiapi.core.app import AppContext
from kiapi.core.file import FileID, FileRecord

from ._operations.get_file import _get_file
from ._operations.get_file_id import _get_file_id
from ._views.file_delete_response import FileDeleteResponse
from ._views.file_list_response import FileListResponse

router = APIRouter(prefix="/v1/files", dependencies=REQUIRE_AUTH)


@router.post("", response_model=FileRecord)
async def upload(
    file: UploadFile = Depends(_get_file),
    ctx: AppContext = Depends(get_ctx),
) -> FileRecord:
    """Store a file and return a reusable file_id.

    Uploaded files become persistent Files API records. Use the returned
    file_id as a FileRef input for generation/editing endpoints, or download
    the bytes later with GET /v1/files/{file_id}/download.
    """
    data = await file.read()
    return ctx.file_store.put_bytes(
        data,
        filename=file.filename or "upload",
        content_type=file.content_type,
    )


@router.get("", response_model=FileListResponse)
async def list_files(ctx: AppContext = Depends(get_ctx)) -> FileListResponse:
    """List stored files.

    Files include explicit uploads and generated artifacts. File records are
    disk-backed and can outlive in-memory jobs across process restarts.
    """
    return FileListResponse(data=ctx.file_store.list())


@router.get("/{file_id}", response_model=FileRecord)
async def get_file(
    file_id: FileID = Depends(_get_file_id),
    ctx: AppContext = Depends(get_ctx),
) -> FileRecord:
    """Get metadata for a stored file.

    This returns metadata only, not file bytes. Use the download endpoint when
    the client needs the artifact body.
    """
    rec = ctx.file_store.get(file_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"unknown file {file_id!r}")
    return rec


@router.get(
    "/{file_id}/download",
    responses={
        200: {
            "description": "Stored file bytes.",
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        },
        404: {"description": "Unknown file_id."},
    },
)
async def download_file(
    file_id: FileID = Depends(_get_file_id),
    ctx: AppContext = Depends(get_ctx),
) -> FileResponse:
    """Download stored file bytes.

    The response media type is the stored file's content_type, such as
    image/png, audio/wav, video/mp4, text/markdown, or application/pdf.
    """
    rec = ctx.file_store.get(file_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"unknown file {file_id!r}")
    return FileResponse(rec.path, media_type=rec.content_type, filename=rec.filename)


@router.delete("/{file_id}", response_model=FileDeleteResponse)
async def delete_file(
    file_id: FileID = Depends(_get_file_id),
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    """Delete a stored file.

    Deleting a file removes the stored bytes and metadata. Existing job records
    may still mention the deleted file_id in artifacts, but the file can no
    longer be downloaded.
    """
    if not ctx.file_store.delete(file_id):
        raise HTTPException(status_code=404, detail=f"unknown file {file_id!r}")
    return {"deleted": True, "file_id": file_id}
