from kiapi.core.capability import CapabilitySpec, capability_spec_registry
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import UrlFileResource

from .._constants.description import DESCRIPTION
from .._models import depthpro


def register() -> None:
    capability_spec_registry.register(
        CapabilitySpec(
            name="depthpro",
            domain="image",
            title="kiapi DepthPro API",
            summary="Estimate depth maps from input images.",
            description=DESCRIPTION,
            openapi_path="/v1/image/depthpro/openapi.json",
            docs_path="/v1/image/depthpro/docs",
            redoc_path="/v1/image/depthpro/redoc",
            path_prefixes=("/v1/image/depthpro",),
        )
    )

    depthpro_url = "https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt"
    model_registry.register(
        ModelSpec(
            name="base",
            family="depthpro",
            domain="image",
            repo="apple/DepthPro",
            module=depthpro,
            weight_gb=2.7,
            peak_headroom_gb=1.2,
            framework="mlx",
            priority=0,
            aliases=("depthpro", "depth-pro", "DepthPro"),
            default=True,
            setup_resources=(
                UrlFileResource(
                    url=depthpro_url,
                    path="~/.cache/mflux/depth_pro/depth_pro.pt",
                    disk_gb=1.8,
                ),
            ),
        )
    )
