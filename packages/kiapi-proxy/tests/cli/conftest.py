from collections.abc import Iterator

import pytest
from kiarina.utils.app import reset


@pytest.fixture(autouse=True)
def reset_app_identity() -> Iterator[None]:
    """Let ``main()`` configure the app identity itself.

    The root conftest pre-configures the app for the API tests, but the CLI
    entry point calls ``configure`` on its own and raises if the identity is
    already set. Clear it here so each CLI invocation starts from a clean slate,
    mirroring a real ``kiapi-proxy`` process.
    """
    reset()
    yield
    reset()
