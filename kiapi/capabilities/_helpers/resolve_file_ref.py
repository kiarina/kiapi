from kiapi.core.file import FileRef, FileStore, ResolvedFileRef
from kiapi.core.file import resolve_file_ref as core_resolve_file_ref

from .._exceptions.CapabilityError import CapabilityError


def resolve_file_ref(
    file_store: FileStore,
    ref: FileRef,
    *,
    kind: str,
) -> ResolvedFileRef:
    try:
        return core_resolve_file_ref(file_store, ref, kind=kind)
    except (FileNotFoundError, ValueError) as exc:
        raise CapabilityError(str(exc)) from exc
