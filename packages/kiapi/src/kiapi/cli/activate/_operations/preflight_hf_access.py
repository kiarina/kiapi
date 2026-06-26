from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote

import click
from huggingface_hub import HfApi, get_token
from huggingface_hub.utils import (
    GatedRepoError,  # pyright: ignore
    HfHubHTTPError,  # pyright: ignore
    LocalTokenNotFoundError,  # pyright: ignore
)

from kiapi.core.setup import HfSnapshotResource, SetupResource


class ResourceStatusManager(Protocol):
    def status(self, resource: SetupResource) -> object: ...


@dataclass(frozen=True)
class HfAccessIssue:
    repo: str
    url: str
    reason: str


def preflight_hf_access(
    resources: list[SetupResource],
    manager: ResourceStatusManager,
    *,
    api: HfApi | None = None,
) -> None:
    """Fail early when selected gated Hugging Face snapshots are not accessible."""

    hf_resources = [
        resource for resource in resources if isinstance(resource, HfSnapshotResource)
    ]
    if not hf_resources:
        return

    api = api or HfApi()
    issues: list[HfAccessIssue] = []
    for resource in hf_resources:
        state = manager.status(resource)
        if bool(getattr(state, "ready", False)):
            continue
        if not _is_gated_repo(api, resource):
            continue

        issue = _check_gated_repo_access(api, resource)
        if issue is not None:
            issues.append(issue)

    if issues:
        raise click.ClickException(_format_hf_access_issues(issues))


def _is_gated_repo(api: HfApi, resource: HfSnapshotResource) -> bool:
    info = api.model_info(
        resource.repo,
        revision=resource.revision,
        token=False,
        timeout=15,
    )
    return bool(getattr(info, "gated", False))


def _check_gated_repo_access(
    api: HfApi, resource: HfSnapshotResource
) -> HfAccessIssue | None:
    url = _repo_url(resource.repo)
    if not get_token():
        return HfAccessIssue(
            repo=resource.repo,
            url=url,
            reason="not authenticated",
        )

    try:
        api.list_repo_files(
            resource.repo,
            revision=resource.revision,
            repo_type="model",
            token=True,
        )
    except LocalTokenNotFoundError:
        return HfAccessIssue(
            repo=resource.repo,
            url=url,
            reason="not authenticated",
        )
    except GatedRepoError:
        return HfAccessIssue(
            repo=resource.repo,
            url=url,
            reason="access has not been approved or terms have not been accepted",
        )
    except HfHubHTTPError as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in {401, 403}:
            return HfAccessIssue(
                repo=resource.repo,
                url=url,
                reason="access has not been approved or terms have not been accepted",
            )
        raise

    return None


def _repo_url(repo: str) -> str:
    return f"https://huggingface.co/{quote(repo, safe='/')}"


def _format_hf_access_issues(issues: list[HfAccessIssue]) -> str:
    repos = "\n".join(
        f"- {issue.repo} ({issue.reason})\n  {issue.url}" for issue in issues
    )
    return (
        "Hugging Face access is required before activation.\n\n"
        "Open the following repository page(s), accept the terms or request access, "
        "then authenticate locally:\n\n"
        f"{repos}\n\n"
        "Authenticate with one of:\n\n"
        "  hf auth login\n\n"
        "or:\n\n"
        "  export HF_TOKEN=hf_...\n\n"
        "Then run `kiapi activate ...` again."
    )
