import typing

import pytest


@pytest.fixture(autouse=True)
def print_test_name(
    request: pytest.FixtureRequest,
) -> typing.Generator[None, None, None]:
    print(f"\n\n--- Running test: {request.node.name} ---")
    yield
    print(f"\n--- Finished test: {request.node.name} ---\n")
