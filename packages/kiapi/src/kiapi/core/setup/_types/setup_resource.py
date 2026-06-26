from typing import Annotated

from pydantic import Field

from .._schemas.docker_image_resource import DockerImageResource
from .._schemas.hf_snapshot_resource import HfSnapshotResource
from .._schemas.local_path_resource import LocalPathResource
from .._schemas.python_package_resource import PythonPackageResource
from .._schemas.python_venv_resource import PythonVenvResource
from .._schemas.url_file_resource import UrlFileResource

SetupResource = Annotated[
    HfSnapshotResource
    | DockerImageResource
    | LocalPathResource
    | UrlFileResource
    | PythonPackageResource
    | PythonVenvResource,
    Field(discriminator="kind"),
]
"""A resource that must be activated before a model can run, tagged by ``kind``."""
