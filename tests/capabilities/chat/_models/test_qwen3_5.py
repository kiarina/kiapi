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


@pytest.mark.parametrize(
    "model,engine_support,expected",
    [
        ("qwen3.8-27b", True, True),
        ("qwen3.8-flash-next", True, True),
        ("qwen3.6-27b", True, False),
        ("qwen3.8-27b", False, False),
    ],
)
def test_image_prefix_integration_preserves_legacy_fallback(
    monkeypatch: Any, tmp_path: Any, model: str, engine_support: bool, expected: bool
) -> None:
    from kiapi.capabilities.chat._views.chat_params import ChatParams

    image = tmp_path / "image"
    image.write_bytes(b"test image")
    work = tmp_path / "work"
    work.mkdir()
    calls = []

    def legacy(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        yield SimpleNamespace(text="ok")

    def supported(*args: Any, apc_image_prefix: bool = False, **kwargs: Any):  # type: ignore[no-untyped-def]
        kwargs["apc_image_prefix"] = apc_image_prefix
        yield from legacy(*args, **kwargs)

    module = ModuleType("mlx_vlm")
    module.stream_generate = supported if engine_support else legacy  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "mlx_vlm", module)
    monkeypatch.setattr(
        qwen3_5, "parse_messages", lambda *args, **kwargs: ([], [str(image)], [], [])
    )
    monkeypatch.setattr(qwen3_5, "create_work_dir", lambda *args: work)
    monkeypatch.setattr(qwen3_5, "_build_prompt", lambda *args: ("prompt", ""))
    monkeypatch.setattr(qwen3_5, "apply_seed", lambda *args: None)
    monkeypatch.setattr(qwen3_5, "limit_to_context", lambda chunks, _: chunks)
    monkeypatch.setattr(
        qwen3_5,
        "collect_generation",
        lambda processor, chunks: ("ok", list(chunks)[-1]),
    )
    monkeypatch.setattr(qwen3_5, "format_response", lambda **kwargs: kwargs)
    monkeypatch.setattr(qwen3_5, "log_apc_result", lambda *args: None)
    payload = SimpleNamespace(
        model=object(),
        processor=object(),
        apc_manager=SimpleNamespace(clear=lambda: None),
        apc_tenant="tenant",
        context_window=32768,
    )
    params = ChatParams(
        model=model,
        messages=[],
        tools=None,
        tool_choice=None,
        parallel_tool_calls=True,
        max_tokens=8,
        temperature=0,
        top_p=1,
        seed=None,
        fps=1,
        use_audio_in_video=False,
        chat_template_kwargs=None,
        stream=False,
    )
    qwen3_5.run(payload, params)
    assert calls[0].get("apc_image_prefix", False) is expected
    if expected:
        assert calls[0]["apc_tenant"] == "tenant"
    else:
        assert calls[0]["apc_tenant"].startswith("tenant:media:")
