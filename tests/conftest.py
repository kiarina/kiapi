import typing

import pytest
from kiarina.utils.app import configure, reset


@pytest.fixture(autouse=True)
def configure_app() -> None:
    # Match runtime: the app identity is set before any user-directory lookup.
    # Reset first so this is safe to run for every test (`configure` raises if the
    # identity is already set).
    reset()
    configure("kiapi", "kiarina")


@pytest.fixture(autouse=True)
def print_test_name(
    request: pytest.FixtureRequest,
) -> typing.Generator[None, None, None]:
    print(f"\n\n--- Running test: {request.node.name} ---")
    yield
    print(f"\n--- Finished test: {request.node.name} ---\n")
