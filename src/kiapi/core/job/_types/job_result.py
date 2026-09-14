from typing import Any

type JobResult = dict[str, Any]
"""A job's result payload. Free-form — its shape depends on the job's
:class:`JobType` (the caller dispatches on the type to read it)."""
