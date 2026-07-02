"""Unified file store. Artifacts and uploads are addressed by ``file_id`` and
outlive in-memory jobs while their files remain on disk.

Public surface (unchanged from the former ``core/file.py``):

  - :class:`FileStore` — put/get/list/delete files under a root directory.
  - :class:`FileRecord` — a stored file's metadata.

See :mod:`._services.file_store` for the on-disk layout and sidecar format.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._helpers.create_file_store import create_file_store
    from ._helpers.resolve_file_ref import resolve_file_ref
    from ._schemas.file_data_url_ref import FileDataURLRef
    from ._schemas.file_id_ref import FileIDRef
    from ._schemas.file_record import FileRecord
    from ._schemas.file_url_ref import FileURLRef
    from ._services.file_store import FileStore
    from ._settings import FileSettings, settings_manager
    from ._types.file_id import FileID
    from ._types.file_ref import FileRef
    from ._views.resolved_file_ref import ResolvedFileRef

__all__ = [
    "FileDataURLRef",
    "FileID",
    "FileIDRef",
    "FileRecord",
    "FileRef",
    "FileSettings",
    "FileStore",
    "FileURLRef",
    "ResolvedFileRef",
    "create_file_store",
    "resolve_file_ref",
    "settings_manager",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "FileDataURLRef": "._schemas.file_data_url_ref",
        "FileID": "._types.file_id",
        "FileIDRef": "._schemas.file_id_ref",
        "FileRecord": "._schemas.file_record",
        "FileRef": "._types.file_ref",
        "FileSettings": "._settings",
        "FileStore": "._services.file_store",
        "FileURLRef": "._schemas.file_url_ref",
        "ResolvedFileRef": "._views.resolved_file_ref",
        "create_file_store": "._helpers.create_file_store",
        "resolve_file_ref": "._helpers.resolve_file_ref",
        "settings_manager": "._settings",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
