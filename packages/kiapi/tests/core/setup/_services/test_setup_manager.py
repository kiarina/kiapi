import subprocess
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from kiapi.core.model import ModelSpec
from kiapi.core.setup import (
    DockerImageResource,
    HfSnapshotResource,
    LocalPathResource,
    PythonPackageResource,
    PythonVenvResource,
    SetupManager,
    SetupRequiredError,
    UrlFileResource,
)


def test_hf_status_uses_local_files_only(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def snapshot_download(**kwargs: object) -> str:
        calls.append(kwargs)
        return "/cache/model"

    monkeypatch.setattr(
        "kiapi.core.setup._services.setup_manager.snapshot_download",
        snapshot_download,
    )

    state = SetupManager().status(HfSnapshotResource(repo="org/model"))

    assert state.ready is True
    assert state.detail == "/cache/model"
    assert calls == [
        {
            "repo_id": "org/model",
            "revision": None,
            "local_dir": None,
            "local_files_only": True,
        }
    ]


def test_hf_status_missing_on_download_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def snapshot_download(**_kwargs: object) -> str:
        raise RuntimeError("not cached")

    monkeypatch.setattr(
        "kiapi.core.setup._services.setup_manager.snapshot_download",
        snapshot_download,
    )

    state = SetupManager().status(HfSnapshotResource(repo="org/model"))

    assert state.ready is False
    assert "not cached" in state.detail


def test_hf_local_dir_status_checks_path(tmp_path: Path) -> None:
    resource = HfSnapshotResource(repo="org/model", local_dir=str(tmp_path))

    assert SetupManager().status(resource).ready is False

    (tmp_path / "config.json").write_text("{}")

    assert SetupManager().status(resource).ready is True


def test_docker_status_uses_image_inspect(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("subprocess.run", run)

    state = SetupManager().status(DockerImageResource(image="repo/image:tag"))

    assert state.ready is True
    assert calls == [["docker", "image", "inspect", "repo/image:tag"]]


def test_docker_status_missing_on_inspect_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(1, cmd, stderr="missing")

    monkeypatch.setattr("subprocess.run", run)

    state = SetupManager().status(DockerImageResource(image="repo/image:tag"))

    assert state.ready is False
    assert state.detail == "missing"


def test_ensure_ready_raises_with_command_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = SetupManager()
    resource = LocalPathResource(path="/missing")
    spec = SimpleNamespace(name="demo", setup_resources=(resource,))

    monkeypatch.setattr(
        manager, "status", lambda _resource: SimpleNamespace(ready=False)
    )

    with pytest.raises(SetupRequiredError) as exc:
        manager.ensure_ready(spec)

    assert "kiapi activate --repo /missing" in str(exc.value)


def test_url_file_status_and_activate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"weights")
    target = tmp_path / "cache" / "weights.bin"
    resource = UrlFileResource(url="https://example.test/weights.bin", path=str(target))
    manager = SetupManager()

    assert manager.status(resource).ready is False

    def urlretrieve(url: str, filename: str | Path) -> tuple[str, object | None]:
        assert url == resource.url
        Path(filename).write_bytes(source.read_bytes())
        return str(filename), None

    monkeypatch.setattr(
        "kiapi.core.setup._services.setup_manager.urllib.request.urlretrieve",
        urlretrieve,
    )

    state = manager.activate(resource)

    assert state.ready is True
    assert target.read_bytes() == b"weights"


def test_python_venv_status_missing_when_python_is_absent(tmp_path: Path) -> None:
    resource = PythonVenvResource(
        path=str(tmp_path / ".venv-demo"),
        packages=("demo-package",),
        import_name="demo",
    )

    state = SetupManager().status(resource)

    assert state.ready is False
    assert "missing:" in state.detail


def test_python_venv_status_imports_check_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    python_path = tmp_path / ".venv-demo" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("")
    resource = PythonVenvResource(
        path=str(tmp_path / ".venv-demo"),
        packages=("demo-package",),
        import_name="demo",
    )
    calls = []

    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("subprocess.run", run)

    state = SetupManager().status(resource)

    assert state.ready is True
    assert state.detail == str(python_path)
    assert calls == [[str(python_path), "-c", "import demo"]]


def test_python_venv_activate_builds_installs_and_checks_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    venv_path = tmp_path / ".venv-demo"
    python_path = venv_path / "bin" / "python"
    resource = PythonVenvResource(
        path=str(venv_path),
        python="3.12",
        packages=("demo-package",),
        import_name="demo",
    )
    calls = []

    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if cmd[:2] == ["uv", "venv"]:
            python_path.parent.mkdir(parents=True)
            python_path.write_text("")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("shutil.which", lambda name: "uv" if name == "uv" else None)
    monkeypatch.setattr("subprocess.run", run)

    state = SetupManager().activate(resource)

    assert state.ready is True
    assert calls == [
        ["uv", "venv", "--python", "3.12", str(venv_path)],
        ["uv", "pip", "install", "--python", str(python_path), "demo-package"],
        [str(python_path), "-c", "import demo"],
    ]


def test_python_venv_activate_falls_back_to_stdlib_venv_and_pip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    venv_path = tmp_path / ".venv-demo"
    python_path = venv_path / "bin" / "python"
    python312 = tmp_path / "python3.12"
    python312.write_text("")
    resource = PythonVenvResource(
        path=str(venv_path),
        python="3.12",
        packages=("demo-package",),
        import_name="demo",
    )
    calls = []

    def which(name: str) -> str | None:
        if name == "uv":
            return None
        if name == "python3.12":
            return str(python312)
        return None

    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if cmd == [str(python312), "-m", "venv", str(venv_path)]:
            python_path.parent.mkdir(parents=True)
            python_path.write_text("")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("shutil.which", which)
    monkeypatch.setattr("subprocess.run", run)

    state = SetupManager().activate(resource)

    assert state.ready is True
    assert calls == [
        [
            str(python312),
            "-c",
            "import sys\nraise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)",
        ],
        [str(python312), "-m", "venv", str(venv_path)],
        [str(python_path), "-m", "pip", "install", "demo-package"],
        [str(python_path), "-c", "import demo"],
    ]


def test_python_venv_activate_skips_ready_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    python_path = tmp_path / ".venv-demo" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("")
    resource = PythonVenvResource(
        path=str(tmp_path / ".venv-demo"),
        packages=("demo-package",),
        import_name="demo",
    )
    calls = []

    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("subprocess.run", run)

    state = SetupManager().activate(resource)

    assert state.ready is True
    assert calls == [[str(python_path), "-c", "import demo"]]


def test_python_venv_deactivate_removes_environment(tmp_path: Path) -> None:
    venv_path = tmp_path / ".venv-demo"
    (venv_path / "bin").mkdir(parents=True)
    (venv_path / "bin" / "python").write_text("")
    resource = PythonVenvResource(
        path=str(venv_path),
        packages=("demo-package",),
        import_name="demo",
    )

    state = SetupManager().deactivate(resource)

    assert state.ready is False
    assert not venv_path.exists()


def test_python_package_resource_label_and_key() -> None:
    resource = PythonPackageResource(
        package="demo-package",
        spec="demo-package @ git+https://example.test/demo.git@abc",
        import_name="demo.module",
        verify_attrs=("run",),
        label_name="demo-git",
    )

    assert resource.label == "demo-git"
    assert resource.key == (
        "python_package:demo-package:"
        "demo-package @ git+https://example.test/demo.git@abc:demo.module:run"
    )


def test_python_package_status_verifies_import_and_attrs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = PythonPackageResource(
        package="demo-package",
        spec="demo-package",
        import_name="demo.module",
        verify_attrs=("PipelineType", "generate_video"),
    )
    calls = []

    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("subprocess.run", run)

    state = SetupManager().status(resource)

    assert state.ready is True
    assert state.detail == "demo.module"
    assert Path(calls[0][0]).name.startswith("python")
    assert calls[0][1] == "-c"
    assert "importlib.import_module('demo.module')" in calls[0][2]
    assert "PipelineType" in calls[0][2]
    assert "generate_video" in calls[0][2]


def test_python_package_status_missing_on_verify_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = PythonPackageResource(
        package="demo-package",
        spec="demo-package",
        import_name="demo.module",
        verify_attrs=("run",),
    )

    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(1, cmd, stderr="missing attrs: ['run']")

    monkeypatch.setattr("subprocess.run", run)

    state = SetupManager().status(resource)

    assert state.ready is False
    assert state.detail == "missing attrs: ['run']"


def test_python_package_activate_installs_into_current_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = PythonPackageResource(
        package="demo-package",
        spec="demo-package @ git+https://example.test/demo.git@abc",
        import_name="demo.module",
    )
    calls = []

    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if cmd[:3] == ["uv", "pip", "install"]:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, cmd, stderr="not installed")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("shutil.which", lambda name: "uv" if name == "uv" else None)
    monkeypatch.setattr("subprocess.run", run)

    state = SetupManager().activate(resource)

    assert state.ready is True
    assert calls[1] == [
        "uv",
        "pip",
        "install",
        "--python",
        calls[0][0],
        "demo-package @ git+https://example.test/demo.git@abc",
    ]


def test_python_package_activate_falls_back_to_current_python_pip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = PythonPackageResource(
        package="demo-package",
        spec="demo-package",
        import_name="demo.module",
    )
    calls = []

    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, cmd, stderr="not installed")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr("subprocess.run", run)

    state = SetupManager().activate(resource)

    assert state.ready is True
    assert calls[1][:4] == [calls[0][0], "-m", "pip", "install"]
    assert calls[1][4:] == ["demo-package"]


def test_python_package_activate_skips_ready_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = PythonPackageResource(
        package="demo-package",
        spec="demo-package",
        import_name="demo.module",
    )
    calls = []

    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("subprocess.run", run)

    state = SetupManager().activate(resource)

    assert state.ready is True
    assert len(calls) == 1
    assert calls[0][1] == "-c"


def test_python_package_deactivate_uninstalls_from_current_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = PythonPackageResource(
        package="demo-package",
        spec="demo-package",
        import_name="demo.module",
    )
    calls = []

    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if cmd[:3] == ["uv", "pip", "uninstall"]:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        raise subprocess.CalledProcessError(1, cmd, stderr="not installed")

    monkeypatch.setattr("shutil.which", lambda name: "uv" if name == "uv" else None)
    monkeypatch.setattr("subprocess.run", run)

    state = SetupManager().deactivate(resource)

    assert state.ready is False
    assert calls[0] == [
        "uv",
        "pip",
        "uninstall",
        "--python",
        calls[1][0],
        "demo-package",
    ]
    assert calls[1][1] == "-c"


def test_python_package_deactivate_falls_back_to_current_python_pip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = PythonPackageResource(
        package="demo-package",
        spec="demo-package",
        import_name="demo.module",
    )
    calls = []

    def run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if len(calls) == 1:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        raise subprocess.CalledProcessError(1, cmd, stderr="not installed")

    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr("subprocess.run", run)

    state = SetupManager().deactivate(resource)

    assert state.ready is False
    assert calls[0][:5] == [calls[1][0], "-m", "pip", "uninstall", "-y"]
    assert calls[0][5:] == ["demo-package"]
    assert calls[1][1] == "-c"


def test_ensure_ready_accepts_ready_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = SetupManager()
    resource = LocalPathResource(path="/ready")
    spec = SimpleNamespace(name="demo", setup_resources=(resource,))

    monkeypatch.setattr(
        manager, "status", lambda _resource: SimpleNamespace(ready=True)
    )

    manager.ensure_ready(spec)


def test_model_spec_protocol_accepts_real_spec(tmp_path: Path) -> None:
    module = ModuleType("fake_handler")
    resource = LocalPathResource(path=str(tmp_path))
    spec = ModelSpec(
        name="demo",
        family="chat",
        domain="chat",
        repo="org/demo",
        module=module,
        weight_gb=1.0,
        peak_headroom_gb=1.0,
        setup_resources=(resource,),
    )

    SetupManager().ensure_ready(spec)
