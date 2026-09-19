import sys
from types import ModuleType, SimpleNamespace
from typing import Any, ClassVar, cast

from kiapi.capabilities.chat._models import qwen3_5


class _FakeAPCManager:
    instances: ClassVar[list["_FakeAPCManager"]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.closed = False
        self.instances.append(self)

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


def test_load_creates_model_scoped_apc_from_settings(monkeypatch: Any) -> None:
    _FakeAPCManager.instances.clear()
    _install_fake_apc(monkeypatch)
    payload = SimpleNamespace()
    monkeypatch.setattr(qwen3_5, "load_mlx_vlm", lambda spec: payload)
    monkeypatch.setattr(qwen3_5.settings_manager, "get_settings", lambda: _settings())

    loaded = qwen3_5.load(cast(Any, SimpleNamespace()))

    manager = _FakeAPCManager.instances[-1]
    assert loaded is payload
    assert loaded.apc_manager is manager
    assert loaded.apc_tenant == "workspace-a"
    assert manager.kwargs == {
        "num_blocks": 128,
        "block_size": 32,
        "overrides": {"memory_max_gb": 2.5},
    }


def test_load_can_disable_apc(monkeypatch: Any) -> None:
    payload = SimpleNamespace()
    monkeypatch.setattr(qwen3_5, "load_mlx_vlm", lambda spec: payload)
    monkeypatch.setattr(
        qwen3_5.settings_manager,
        "get_settings",
        lambda: _settings(enabled=False),
    )

    loaded = qwen3_5.load(cast(Any, SimpleNamespace()))

    assert loaded.apc_manager is None
    assert loaded.apc_tenant == "workspace-a"


def test_release_closes_apc_manager() -> None:
    manager = _FakeAPCManager()

    qwen3_5.release(SimpleNamespace(apc_manager=manager))

    assert manager.closed
