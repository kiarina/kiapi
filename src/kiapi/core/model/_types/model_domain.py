from typing import Literal

ModelDomain = Literal["chat", "embedding", "audio", "video", "image", "web"]
"""The modality bucket used for discovery/grouping. A fixed, closed set — every
family belongs to exactly one domain. Generation endpoints are organized as
``/v1/<domain>/<family>/<op>``."""
