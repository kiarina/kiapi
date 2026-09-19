from types import SimpleNamespace

from .._settings import settings_manager


def initialize_apc(payload: SimpleNamespace) -> None:
    settings = settings_manager.get_settings()
    payload.apc_manager = None
    payload.apc_tenant = settings.apc_tenant
    if settings.apc_enabled:
        from mlx_vlm.apc import APCManager

        payload.apc_manager = APCManager(
            num_blocks=settings.apc_num_blocks,
            block_size=settings.apc_block_size,
            overrides={"memory_max_gb": settings.apc_memory_max_gb},
        )
