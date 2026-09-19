import sys
from types import ModuleType, SimpleNamespace
from typing import Any, ClassVar, cast

import pytest

from kiapi.capabilities.chat._models import qwen3_5, qwen3_omni
from kiapi.capabilities.chat._settings import settings_manager


class _FakeAPCManager:
    instances: ClassVar[list["_FakeAPCManager"]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.closed = False
        self.cleared = False
        self.instances.append(self)

    def clear(self) -> None:
        self.cleared = True

    def close(self) -> None:
        self.closed = True


def _settings(*, enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        apc_enabled=enabled,
        apc_num_blocks=128,
        apc_block_size=32,
        apc_memory_max_gb=2.5,
        apc_tenant="workspace-a",
    )


def _install_fake_apc(monkeypatch: Any) -> None:
    module = ModuleType("mlx_vlm.apc")
    module.APCManager = _FakeAPCManager  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "mlx_vlm.apc", module)


@pytest.mark.parametrize("handler", [qwen3_5, qwen3_omni])
def test_load_creates_model_scoped_apc_from_settings(
    monkeypatch: Any, handler: Any
) -> None:
    _FakeAPCManager.instances.clear()
    _install_fake_apc(monkeypatch)
    payload = SimpleNamespace()
    monkeypatch.setattr(handler, "load_mlx_vlm", lambda spec: payload)
    monkeypatch.setattr(settings_manager, "get_settings", lambda: _settings())

    loaded = handler.load(cast(Any, SimpleNamespace()))

    manager = _FakeAPCManager.instances[-1]
    assert loaded is payload
    assert loaded.apc_manager is manager
    assert loaded.apc_tenant == "workspace-a"
    assert manager.kwargs == {
        "num_blocks": 128,
        "block_size": 32,
        "overrides": {"memory_max_gb": 2.5},
    }


@pytest.mark.parametrize("handler", [qwen3_5, qwen3_omni])
def test_load_can_disable_apc(monkeypatch: Any, handler: Any) -> None:
    payload = SimpleNamespace()
    monkeypatch.setattr(handler, "load_mlx_vlm", lambda spec: payload)
    monkeypatch.setattr(
        settings_manager,
        "get_settings",
        lambda: _settings(enabled=False),
    )

    loaded = handler.load(cast(Any, SimpleNamespace()))

    assert loaded.apc_manager is None
    assert loaded.apc_tenant == "workspace-a"


@pytest.mark.parametrize("handler", [qwen3_5, qwen3_omni])
def test_release_closes_apc_manager(handler: Any) -> None:
    manager = _FakeAPCManager()

    handler.release(SimpleNamespace(apc_manager=manager))

    assert manager.closed and manager.cleared
