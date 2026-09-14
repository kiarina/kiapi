from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class FileSettings(BaseSettings):
    """Settings for the file store that keeps uploads and generated artifacts."""

    model_config = SettingsConfigDict(env_prefix="KIAPI_")

    files_root: str = Field(
        default="/tmp/kiapi/files",
        title="File storage directory",
        description=(
            "Directory where uploaded files and generated artifacts are stored.\n"
            "The default is under /tmp so files may disappear after reboot or tmp cleanup.\n"
            "~ is expanded as the home directory of the running user."
        ),
    )


settings_manager = SettingsManager(FileSettings)
