import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from huggingface_hub import scan_cache_dir, snapshot_download

from .._exceptions.setup_required_error import SetupRequiredError
from .._schemas.docker_image_resource import DockerImageResource
from .._schemas.hf_snapshot_resource import HfSnapshotResource
from .._schemas.local_path_resource import LocalPathResource
from .._schemas.python_package_resource import PythonPackageResource
from .._schemas.python_venv_resource import PythonVenvResource
from .._schemas.setup_status import SetupStatus
from .._schemas.url_file_resource import UrlFileResource
from .._types.setup_resource import SetupResource
from .._types.setup_target import SetupTarget


class SetupManager:
    def status(self, resource: SetupResource) -> SetupStatus:
        if isinstance(resource, HfSnapshotResource):
            return self._hf_status(resource)
        if isinstance(resource, DockerImageResource):
            return self._docker_status(resource)
        if isinstance(resource, LocalPathResource):
            path = Path(resource.path).expanduser()
            if path.exists():
                return SetupStatus(True, str(path))
            return SetupStatus(False, f"missing: {path}")
        if isinstance(resource, UrlFileResource):
            path = Path(resource.path).expanduser()
            if path.exists() and path.stat().st_size > 0:
                return SetupStatus(True, str(path))
            return SetupStatus(False, f"missing: {path}")
        if isinstance(resource, PythonVenvResource):
            return self._python_venv_status(resource)
        if isinstance(resource, PythonPackageResource):
            return self._python_package_status(resource)

    def activate(self, resource: SetupResource) -> SetupStatus:
        if isinstance(resource, HfSnapshotResource):
            snapshot_path = snapshot_download(
                repo_id=resource.repo,
                revision=resource.revision,
                local_dir=resource.local_dir,
            )
            return SetupStatus(True, str(snapshot_path))
        if isinstance(resource, DockerImageResource):
            self._docker("pull", resource.image)
            return self.status(resource)
        if isinstance(resource, LocalPathResource):
            return self.status(resource)
        if isinstance(resource, UrlFileResource):
            file_path = Path(resource.path).expanduser()
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if not file_path.exists():
                with tempfile.NamedTemporaryFile(
                    dir=file_path.parent, delete=False
                ) as tmp_file:
                    tmp_path = Path(tmp_file.name)
                try:
                    urllib.request.urlretrieve(resource.url, tmp_path)
                    tmp_path.replace(file_path)
                finally:
                    tmp_path.unlink(missing_ok=True)
            return self.status(resource)
        if isinstance(resource, PythonVenvResource):
            return self._python_venv_activate(resource)
        if isinstance(resource, PythonPackageResource):
            return self._python_package_activate(resource)

    def deactivate(self, resource: SetupResource) -> SetupStatus:
        if isinstance(resource, HfSnapshotResource):
            return self._hf_deactivate(resource)
        if isinstance(resource, DockerImageResource):
            self._docker("image", "rm", resource.image)
            return self.status(resource)
        if isinstance(resource, LocalPathResource):
            path = Path(resource.path).expanduser()
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            return self.status(resource)
        if isinstance(resource, UrlFileResource):
            Path(resource.path).expanduser().unlink(missing_ok=True)
            return self.status(resource)
        if isinstance(resource, PythonVenvResource):
            path = Path(resource.path).expanduser()
            if path.exists():
                shutil.rmtree(path)
            return self.status(resource)
        if isinstance(resource, PythonPackageResource):
            return self._python_package_deactivate(resource)

    def ensure_ready(self, spec: SetupTarget) -> None:
        missing = [
            resource
            for resource in spec.setup_resources
            if not self.status(resource).ready
        ]
        if not missing:
            return

        labels = ", ".join(resource.label for resource in missing)
        repos = " ".join(f"--repo {resource.label}" for resource in missing)
        raise SetupRequiredError(
            f"model {spec.name!r} is not activated; missing: {labels}. "
            f"Run: kiapi activate {repos}"
        )

    def _hf_status(self, resource: HfSnapshotResource) -> SetupStatus:
        if resource.local_dir is not None:
            local_path = Path(resource.local_dir).expanduser()
            if local_path.exists() and any(local_path.iterdir()):
                return SetupStatus(True, str(local_path))
            return SetupStatus(False, f"missing: {local_path}")

        try:
            snapshot_path = snapshot_download(
                repo_id=resource.repo,
                revision=resource.revision,
                local_dir=resource.local_dir,
                local_files_only=True,
            )
        except Exception as exc:
            return SetupStatus(False, str(exc))
        return SetupStatus(True, str(snapshot_path))

    def _hf_deactivate(self, resource: HfSnapshotResource) -> SetupStatus:
        if resource.local_dir is not None:
            path = Path(resource.local_dir).expanduser()
            if path.exists():
                shutil.rmtree(path)
            return self.status(resource)

        info = scan_cache_dir()
        revisions: list[str] = []
        for repo in info.repos:
            if repo.repo_id != resource.repo:
                continue
            for revision in repo.revisions:
                revisions.append(revision.commit_hash)

        if revisions:
            strategy = info.delete_revisions(*revisions)
            strategy.execute()

        return self.status(resource)

    def _docker_status(self, resource: DockerImageResource) -> SetupStatus:
        try:
            self._docker("image", "inspect", resource.image)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            return SetupStatus(False, detail)
        return SetupStatus(True, "present")

    def _docker(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["docker", *args],
            check=True,
            text=True,
            capture_output=True,
        )

    def _python_venv_status(self, resource: PythonVenvResource) -> SetupStatus:
        python_path = self._python_venv_python_path(resource)
        if not python_path.exists():
            return SetupStatus(False, f"missing: {python_path}")
        try:
            self._run_python_import(python_path, resource.import_name)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            return SetupStatus(False, detail)
        return SetupStatus(True, str(python_path))

    def _python_venv_activate(self, resource: PythonVenvResource) -> SetupStatus:
        state = self.status(resource)
        if state.ready:
            return state

        path = Path(resource.path).expanduser()
        python_path = self._python_venv_python_path(resource)
        if not python_path.exists():
            self._create_python_venv(path, resource.python)
        self._install_python_packages(python_path, resource.packages)
        return self.status(resource)

    def _python_venv_python_path(self, resource: PythonVenvResource) -> Path:
        return Path(resource.path).expanduser() / "bin" / "python"

    def _run_python_import(self, python_path: Path, import_name: str) -> None:
        subprocess.run(
            [str(python_path), "-c", f"import {import_name}"],
            check=True,
            text=True,
            capture_output=True,
        )

    def _python_package_status(self, resource: PythonPackageResource) -> SetupStatus:
        try:
            self._run_python_package_verify(resource)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            return SetupStatus(False, detail)
        return SetupStatus(True, resource.import_name)

    def _python_package_activate(self, resource: PythonPackageResource) -> SetupStatus:
        state = self.status(resource)
        if state.ready:
            return state

        self._install_python_packages(Path(sys.executable), (resource.spec,))
        return self.status(resource)

    def _python_package_deactivate(
        self, resource: PythonPackageResource
    ) -> SetupStatus:
        self._uninstall_python_package(Path(sys.executable), resource.package)
        return self.status(resource)

    def _run_python_package_verify(self, resource: PythonPackageResource) -> None:
        code = "\n".join(
            [
                "import importlib",
                f"module = importlib.import_module({resource.import_name!r})",
                f"attrs = {list(resource.verify_attrs)!r}",
                "missing = [attr for attr in attrs if not hasattr(module, attr)]",
                "if missing:",
                "    raise RuntimeError(f'missing attrs: {missing}')",
            ]
        )
        subprocess.run(
            [sys.executable, "-c", code],
            check=True,
            text=True,
            capture_output=True,
        )

    def _create_python_venv(self, path: Path, python: str) -> None:
        if shutil.which("uv"):
            subprocess.run(
                ["uv", "venv", "--python", python, str(path)],
                check=True,
                text=True,
                capture_output=True,
            )
            return

        python_bin = self._resolve_python_executable(python)
        subprocess.run(
            [str(python_bin), "-m", "venv", str(path)],
            check=True,
            text=True,
            capture_output=True,
        )

    def _install_python_packages(
        self, python_path: Path, packages: tuple[str, ...]
    ) -> None:
        if shutil.which("uv"):
            subprocess.run(
                ["uv", "pip", "install", "--python", str(python_path), *packages],
                check=True,
                text=True,
                capture_output=True,
            )
            return

        subprocess.run(
            [str(python_path), "-m", "pip", "install", *packages],
            check=True,
            text=True,
            capture_output=True,
        )

    def _uninstall_python_package(self, python_path: Path, package: str) -> None:
        if shutil.which("uv"):
            subprocess.run(
                ["uv", "pip", "uninstall", "--python", str(python_path), package],
                check=True,
                text=True,
                capture_output=True,
            )
            return

        subprocess.run(
            [str(python_path), "-m", "pip", "uninstall", "-y", package],
            check=True,
            text=True,
            capture_output=True,
        )

    def _resolve_python_executable(self, python: str) -> Path:
        candidates = [python]
        if python.startswith("3."):
            candidates.append(f"python{python}")
        candidates.extend(["python3", sys.executable])

        for candidate in candidates:
            executable = (
                shutil.which(candidate) if candidate != sys.executable else candidate
            )
            if executable and self._python_matches_requirement(
                Path(executable), python
            ):
                return Path(executable)

        raise RuntimeError(f"Python {python} executable was not found")

    def _python_matches_requirement(self, python_path: Path, python: str) -> bool:
        if not python.startswith("3."):
            return True

        code = "\n".join(
            [
                "import sys",
                f"raise SystemExit(0 if sys.version_info[:2] == {tuple(map(int, python.split('.')))!r} else 1)",
            ]
        )
        result = subprocess.run(
            [str(python_path), "-c", code],
            text=True,
            capture_output=True,
        )
        return result.returncode == 0
