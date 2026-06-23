import pytest

from kiapi.core.job import JobStatus, JobStore


@pytest.fixture
def store() -> JobStore:
    return JobStore()


def test_create_registers_job(store: JobStore) -> None:
    job = store.create("chat", {"prompt": "hi"})

    assert job.type == "chat"
    assert job.params == {"prompt": "hi"}
    assert job.status is JobStatus.QUEUED
    assert store.get(job.id) is job


def test_create_defaults_params_to_empty_dict(store: JobStore) -> None:
    job = store.create("chat")

    assert job.params == {}


def test_get_unknown_returns_none(store: JobStore) -> None:
    assert store.get("job_missing") is None


def test_list_all_empty(store: JobStore) -> None:
    assert store.list_all() == []


def test_list_all_is_newest_first(store: JobStore) -> None:
    a = store.create("chat")
    a.created_at = 100.0
    b = store.create("chat")
    b.created_at = 200.0
    c = store.create("chat")
    c.created_at = 300.0

    assert [j.id for j in store.list_all()] == [c.id, b.id, a.id]


def test_delete_removes_and_returns_job(store: JobStore) -> None:
    job = store.create("chat")

    assert store.delete(job.id) is job
    assert store.get(job.id) is None


def test_delete_unknown_returns_none(store: JobStore) -> None:
    assert store.delete("job_missing") is None
