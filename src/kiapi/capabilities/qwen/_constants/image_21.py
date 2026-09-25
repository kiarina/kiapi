IMAGE_21_VARIANT = "image-2.1"

# Qwen-Image-2.1 editing lives in the mflux fork pinned by pyproject.toml
# (mflux-community/mflux#741); a published wheel falls back to official mflux.
# Import through the package: importing the variant module first is circular.
IMAGE_21_EDIT_MODULE = "mflux.models.qwen21.reference"
