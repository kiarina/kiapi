from collections.abc import Callable

from kiapi.core.file import FileID
from kiapi.core.job import JobResult

type JobThunk = Callable[[], tuple[JobResult, list[FileID]]]
