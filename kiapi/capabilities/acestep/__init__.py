"""acestep family - ACE-Step 1.5 music generation, run in an isolated venv subprocess.

Endpoints: ``POST /v1/audio/acestep/{generate,cover,repaint,extract}``. ace-step
pins transformers 4.x, which conflicts with chat/embedding's transformers 5.x, so
it cannot share kiapi's process. Instead each variant (preset) is a resident spec
whose payload is a long-lived worker subprocess (launched from the ACE-Step venv);
kiapi talks to it over a small JSON pipe protocol and treats it as a normal
resident model - budgeted, evictable (``release`` = terminate), TTL-swept.

The subprocess's memory is NOT visible in kiapi's own RSS, so ``weight_gb`` here
is an estimate (the registry value is authoritative for budgeting); load() logs
the child's real RSS so these can be tuned on device.
"""

from ._helpers.register import register
from ._operations.handle_cover import handle_cover
from ._operations.handle_extract import handle_extract
from ._operations.handle_generate import handle_generate
from ._operations.handle_repaint import handle_repaint
from ._settings import settings_manager
from ._views.cover_request import CoverRequest
from ._views.extract_request import ExtractRequest
from ._views.generate_request import GenerateRequest
from ._views.repaint_request import RepaintRequest

__all__ = [
    "CoverRequest",
    "ExtractRequest",
    "GenerateRequest",
    "RepaintRequest",
    "handle_cover",
    "handle_extract",
    "handle_generate",
    "handle_repaint",
    "register",
    "settings_manager",
]
