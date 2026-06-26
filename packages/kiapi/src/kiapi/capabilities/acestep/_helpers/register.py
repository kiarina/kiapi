"""Register acestep's models + OpenAPI description in the global registries."""

import os

from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import HfSnapshotResource, PythonVenvResource

from .._constants.description import DESCRIPTION
from .._models import acestep
from .._operations.resolve_ace_step_paths import resolve_ace_step_paths
from .._settings import settings_manager

_ACESTEP_PACKAGE = "ace-step @ git+https://github.com/ace-step/ACE-Step-1.5.git"


def register() -> None:
    paths = resolve_ace_step_paths(settings_manager.get_settings())
    capability_spec_registry.register(
        CapabilitySpec(
            name="acestep",
            domain="audio",
            title="kiapi ACE-Step API",
            summary="Generate songs, covers, repaints, and stems with ACE-Step.",
            description=DESCRIPTION,
            openapi_path="/v1/audio/acestep/openapi.json",
            docs_path="/v1/audio/acestep/docs",
            redoc_path="/v1/audio/acestep/redoc",
            path_prefixes=("/v1/audio/acestep",),
        )
    )

    # framework="rss" -> kiapi-RSS-based measurement (child RSS not captured, so the
    # estimate below is what the budget uses). resident=True -> held until evicted/TTL.
    model_registry.register(
        ModelSpec(
            name="xl-base",
            family="acestep",
            domain="audio",
            repo="acestep-v15-xl-base",
            module=acestep,
            weight_gb=27.0,  # est. turbo 12.2 GB + (19-4.5) DiT delta
            peak_headroom_gb=6.0,
            framework="rss",
            priority=0,
            default=True,
            setup_resources=(
                PythonVenvResource(
                    path=paths.venv_path,
                    python="3.12",
                    packages=(os.environ.get("KIAPI_ACESTEP_SPEC", _ACESTEP_PACKAGE),),
                    import_name="acestep",
                    label_name="acestep-venv",
                    disk_gb=1.3,
                ),
                HfSnapshotResource(
                    repo="ACE-Step/Ace-Step1.5",
                    disk_gb=9.4,
                    local_dir=paths.checkpoint_dir,
                ),
                HfSnapshotResource(
                    repo="ACE-Step/acestep-v15-xl-base",
                    disk_gb=19.0,
                    local_dir=f"{paths.checkpoint_dir}/acestep-v15-xl-base",
                ),
            ),
        )
    )
    model_registry.register(
        ModelSpec(
            name="turbo",
            family="acestep",
            domain="audio",
            repo="acestep-v15-turbo",
            module=acestep,
            weight_gb=12.0,  # measured child RSS ~12.2 GB (LLM + turbo DiT)
            peak_headroom_gb=4.0,
            framework="rss",
            priority=0,
            setup_resources=(
                PythonVenvResource(
                    path=paths.venv_path,
                    python="3.12",
                    packages=(os.environ.get("KIAPI_ACESTEP_SPEC", _ACESTEP_PACKAGE),),
                    import_name="acestep",
                    label_name="acestep-venv",
                    disk_gb=1.3,
                ),
                HfSnapshotResource(
                    repo="ACE-Step/Ace-Step1.5",
                    disk_gb=9.4,
                    local_dir=paths.checkpoint_dir,
                ),
            ),
        )
    )
