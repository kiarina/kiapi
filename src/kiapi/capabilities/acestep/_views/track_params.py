from .cover_params import CoverParams
from .extract_params import ExtractParams
from .generate_params import GenerateParams
from .repaint_params import RepaintParams

type TrackParams = GenerateParams | CoverParams | RepaintParams | ExtractParams
"""Any one ACE-Step subprocess generation contract."""
