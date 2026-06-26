from kiapi.core.file import FileRef, FileStore, resolve_file_ref

from .._exceptions.CapabilityError import CapabilityError


def get_file_path(
    file_store: FileStore,
    file: str | FileRef,
    *,
    kind: str,
) -> str:
    try:
        if isinstance(file, str):
            rec = file_store.get(file)
            if rec is None:
                raise FileNotFoundError(f"unknown {kind} file_id {file!r}")
            return rec.path
        return resolve_file_ref(file_store, file, kind=kind).path
    except (FileNotFoundError, ValueError) as exc:
        raise CapabilityError(str(exc)) from exc
