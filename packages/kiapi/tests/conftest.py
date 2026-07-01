import typing

import pytest


@pytest.fixture(scope="session", autouse=True)
def configure_app() -> None:
    # Match runtime: the CLI and ASGI app set the application identity before any
    # user-directory lookup. Tests exercise those helpers directly, so configure
    # once for the whole session.
    from kiapi.core.app import configure_app as _configure_app

    _configure_app()


@pytest.fixture(autouse=True)
def print_test_name(
    request: pytest.FixtureRequest,
) -> typing.Generator[None, None, None]:
    print(f"\n\n--- Running test: {request.node.name} ---")
    yield
    print(f"\n--- Finished test: {request.node.name} ---\n")
