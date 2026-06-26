from dataclasses import dataclass

from .._schemas.file_record import FileRecord


@dataclass(frozen=True)
class ResolvedFileRef:
    record: FileRecord

    @property
    def file_id(self) -> str:
        return self.record.file_id

    @property
    def path(self) -> str:
        return self.record.path
