"""Split a flux2 spec repo into ``(model_name, role)``.

A role marker is appended to a spec's ``repo`` as ``<repo>#<role>`` so a single
family registration can yield distinct resident models per role (generate/edit).
A bare repo means the default ``generate`` role.
"""


def split_repo(repo: str) -> tuple[str, str]:
    base, sep, role = repo.partition("#")
    return base, role if sep else "generate"
