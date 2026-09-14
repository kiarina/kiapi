type JobType = str
"""Names the operation a job runs (e.g. ``"chat"``, ``"acestep.generate"``,
``"ltx2"``). The caller dispatches on it, and it determines the shape of the
job's ``result``."""
