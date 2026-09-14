from kiapi.capabilities.acestep import register as register_acestep
from kiapi.capabilities.audiogen import register as register_audiogen
from kiapi.capabilities.chat import register as register_chat
from kiapi.capabilities.depthpro import register as register_depthpro
from kiapi.capabilities.embedding import register as register_embedding
from kiapi.capabilities.ernie import register as register_ernie
from kiapi.capabilities.flux2 import register as register_flux2
from kiapi.capabilities.ideogram4 import register as register_ideogram4
from kiapi.capabilities.ltx2 import register as register_ltx2
from kiapi.capabilities.qwen import register as register_qwen
from kiapi.capabilities.seedvr2 import register as register_seedvr2
from kiapi.capabilities.web import register as register_web
from kiapi.capabilities.zimage import register as register_zimage

_registered = False


def register_all_capabilities() -> None:
    global _registered
    if _registered:
        return

    # Capability registration resolves user directories (e.g. ACE-Step paths),
    # so the application identity must already be configured by the caller (the
    # CLI entry, the ASGI factory, the docs build, or the test fixtures).
    register_acestep()
    register_audiogen()
    register_chat()
    register_depthpro()
    register_embedding()
    register_ernie()
    register_flux2()
    register_ideogram4()
    register_ltx2()
    register_qwen()
    register_seedvr2()
    register_web()
    register_zimage()
    _registered = True
