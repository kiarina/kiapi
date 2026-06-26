from types import SimpleNamespace

import click
import httpx
import pytest
from huggingface_hub.utils import HfHubHTTPError

from kiapi.cli.activate._operations import preflight_hf_access as subject
from kiapi.core.setup import HfSnapshotResource, LocalPathResource


class FakeManager:
    def __init__(self, *, ready: bool = False) -> None:
        self.ready = ready
        self.status_calls: list[object] = []

    def status(self, resource: object) -> SimpleNamespace:
        self.status_calls.append(resource)
        return SimpleNamespace(ready=self.ready)


class FakeApi:
    def __init__(
        self,
        *,
        gated: bool | str = False,
        list_error: Exception | None = None,
    ) -> None:
        self.gated = gated
        self.list_error = list_error
        self.model_info_calls: list[dict[str, object]] = []
        self.list_repo_files_calls: list[dict[str, object]] = []

    def model_info(self, repo: str, **kwargs: object) -> SimpleNamespace:
        self.model_info_calls.append({"repo": repo, **kwargs})
        return SimpleNamespace(gated=self.gated)

    def list_repo_files(self, repo: str, **kwargs: object) -> list[str]:
        self.list_repo_files_calls.append({"repo": repo, **kwargs})
        if self.list_error is not None:
            raise self.list_error
        return ["config.json"]


def test_preflight_ignores_non_hf_resources() -> None:
    api = FakeApi(gated=True)

    subject.preflight_hf_access(
        [LocalPathResource(path="/tmp/model")],
        FakeManager(),
        api=api,  # type: ignore[arg-type]
    )

    assert api.model_info_calls == []


def test_preflight_skips_ready_hf_snapshot() -> None:
    resource = HfSnapshotResource(repo="org/gated-model")
    api = FakeApi(gated=True)

    subject.preflight_hf_access(
        [resource],
        FakeManager(ready=True),
        api=api,  # type: ignore[arg-type]
    )

    assert api.model_info_calls == []


def test_preflight_allows_public_hf_snapshot() -> None:
    resource = HfSnapshotResource(repo="org/public-model")
    api = FakeApi(gated=False)

    subject.preflight_hf_access(
        [resource],
        FakeManager(),
        api=api,  # type: ignore[arg-type]
    )

    assert api.model_info_calls == [
        {
            "repo": "org/public-model",
            "revision": None,
            "token": False,
            "timeout": 15,
        }
    ]
    assert api.list_repo_files_calls == []


def test_preflight_reports_gated_snapshot_without_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = HfSnapshotResource(repo="org/gated-model")
    api = FakeApi(gated="auto")
    monkeypatch.setattr(subject, "get_token", lambda: None)

    with pytest.raises(click.ClickException) as exc:
        subject.preflight_hf_access(
            [resource],
            FakeManager(),
            api=api,  # type: ignore[arg-type]
        )

    message = str(exc.value)
    assert "org/gated-model" in message
    assert "https://huggingface.co/org/gated-model" in message
    assert "hf auth login" in message
    assert "export HF_TOKEN=hf_..." in message
    assert api.list_repo_files_calls == []


def test_preflight_allows_accessible_gated_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = HfSnapshotResource(repo="org/gated-model", revision="main")
    api = FakeApi(gated="auto")
    monkeypatch.setattr(subject, "get_token", lambda: "hf_test")

    subject.preflight_hf_access(
        [resource],
        FakeManager(),
        api=api,  # type: ignore[arg-type]
    )

    assert api.list_repo_files_calls == [
        {
            "repo": "org/gated-model",
            "revision": "main",
            "repo_type": "model",
            "token": True,
        }
    ]


def test_preflight_reports_gated_snapshot_without_approved_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = HfSnapshotResource(repo="org/gated-model")
    response = httpx.Response(403, request=httpx.Request("GET", "https://hf.test"))
    api = FakeApi(
        gated="auto",
        list_error=HfHubHTTPError("forbidden", response=response),
    )
    monkeypatch.setattr(subject, "get_token", lambda: "hf_test")

    with pytest.raises(click.ClickException) as exc:
        subject.preflight_hf_access(
            [resource],
            FakeManager(),
            api=api,  # type: ignore[arg-type]
        )

    assert "access has not been approved or terms have not been accepted" in str(
        exc.value
    )
    assert "https://huggingface.co/org/gated-model" in str(exc.value)
