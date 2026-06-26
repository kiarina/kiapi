"""flux2 family — FLUX.2 Klein generation/edit/LoRA-training via mflux.

Endpoints: ``POST /v1/image/flux2/{generate,edit,train}``. ``generate`` is
text-to-image (img2img when ``init_image_file_id`` is supplied), ``edit`` is
multi-reference image editing, and ``train`` LoRA-finetunes base variants on
captioned images or ``*_in`` / ``*_out`` edit pairs (always async). LoRA adapters
and a ``quantize`` override run on a one-off transient model; otherwise the
resident model is used.
"""

from kiapi.capabilities import ValidationError

from ._helpers.register import register
from ._helpers.validate_edit import validate_edit
from ._helpers.validate_generate import validate_generate
from ._operations.handle_edit import handle_edit
from ._operations.handle_generate import handle_generate
from ._operations.handle_train import handle_train
from ._settings import settings_manager
from ._views.edit_request import EditRequest
from ._views.generate_request import GenerateRequest
from ._views.train_request import TrainRequest

__all__ = [
    "EditRequest",  # ._views
    "GenerateRequest",  # ._views
    "TrainRequest",  # ._views
    "ValidationError",  # kiapi.capabilities
    "handle_edit",  # ._operations
    "handle_generate",  # ._operations
    "handle_train",  # ._operations
    "register",  # ._helpers
    "settings_manager",  # ._settings
    "validate_edit",  # ._helpers
    "validate_generate",  # ._helpers
]
