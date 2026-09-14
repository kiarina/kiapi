from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._exceptions.setup_required_error import SetupRequiredError
    from ._schemas.docker_image_resource import DockerImageResource
    from ._schemas.hf_snapshot_resource import HfSnapshotResource
    from ._schemas.local_path_resource import LocalPathResource
    from ._schemas.python_package_resource import PythonPackageResource
    from ._schemas.python_venv_resource import PythonVenvResource
    from ._schemas.setup_status import SetupStatus
    from ._schemas.url_file_resource import UrlFileResource
    from ._services.setup_manager import SetupManager
    from ._types.setup_resource import SetupResource
    from ._types.setup_target import SetupTarget

__all__ = [
    "DockerImageResource",
    "HfSnapshotResource",
    "LocalPathResource",
    "PythonPackageResource",
    "PythonVenvResource",
    "SetupManager",
    "SetupRequiredError",
    "SetupResource",
    "SetupStatus",
    "SetupTarget",
    "UrlFileResource",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "DockerImageResource": "._schemas.docker_image_resource",
        "HfSnapshotResource": "._schemas.hf_snapshot_resource",
        "LocalPathResource": "._schemas.local_path_resource",
        "PythonPackageResource": "._schemas.python_package_resource",
        "PythonVenvResource": "._schemas.python_venv_resource",
        "SetupManager": "._services.setup_manager",
        "SetupRequiredError": "._exceptions.setup_required_error",
        "SetupResource": "._types.setup_resource",
        "SetupStatus": "._schemas.setup_status",
        "SetupTarget": "._types.setup_target",
        "UrlFileResource": "._schemas.url_file_resource",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
