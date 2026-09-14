from collections.abc import Iterable

from kiapi.core.model import ModelSpec
from kiapi.core.setup import SetupResource


def dedupe_resources(specs: Iterable[ModelSpec]) -> list[SetupResource]:
    resources: dict[str, SetupResource] = {}
    for spec in specs:
        for resource in spec.setup_resources:
            resources.setdefault(resource.key, resource)
    return list(resources.values())
