type JobID = str
"""The address of a job (``"job_<hex>"``). Async requests return it immediately;
clients poll the job by this id. Jobs are in-memory, so it is not persistent."""
