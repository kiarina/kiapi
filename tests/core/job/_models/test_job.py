from kiapi.core.job import Job, JobStatus


def test_defaults() -> None:
    job = Job(type="chat")

    assert job.type == "chat"
    assert job.params == {}
    assert job.id.startswith("job_")
    assert job.status is JobStatus.QUEUED
    assert job.result is None
    assert job.artifacts == []
    assert job.error is None
    assert job.created_at > 0
    assert job.started_at is None
    assert job.finished_at is None


def test_ids_are_unique() -> None:
    assert Job(type="chat").id != Job(type="chat").id


def test_mark_running() -> None:
    job = Job(type="chat")

    job.mark_running()

    assert job.status is JobStatus.RUNNING
    assert job.started_at is not None


def test_mark_succeeded() -> None:
    job = Job(type="chat")

    job.mark_succeeded({"text": "hi"}, ["file_abc"])

    assert job.status is JobStatus.SUCCEEDED
    assert job.result == {"text": "hi"}
    assert job.artifacts == ["file_abc"]
    assert job.finished_at is not None
    assert job.error is None


def test_mark_failed() -> None:
    job = Job(type="chat")

    job.mark_failed("boom")

    assert job.status is JobStatus.FAILED
    assert job.error == "boom"
    assert job.finished_at is not None


def test_mark_canceled() -> None:
    job = Job(type="chat")

    job.mark_canceled()

    assert job.status is JobStatus.CANCELED
    assert job.finished_at is not None


def test_to_dict_roundtrips_fields() -> None:
    job = Job(type="chat", params={"prompt": "x"})
    job.mark_succeeded({"text": "hi"}, ["file_1"])

    d = job.to_dict()

    assert d["type"] == "chat"
    assert d["params"] == {"prompt": "x"}
    assert d["id"] == job.id
    assert d["status"] == JobStatus.SUCCEEDED
    assert d["result"] == {"text": "hi"}
    assert d["artifacts"] == ["file_1"]
