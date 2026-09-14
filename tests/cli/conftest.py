import pytest
from kiarina.utils.app import reset


@pytest.fixture(autouse=True)
def fresh_app_identity() -> None:
    # Each `CliRunner().invoke(main, ...)` models a fresh `kiapi ...` process,
    # which starts unconfigured and sets the identity in the CLI entry. The root
    # `configure_app` fixture leaves the identity set, so reset here (after it
    # runs) to give the CLI entry a clean slate.
    reset()
