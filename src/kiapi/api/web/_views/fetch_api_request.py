from pydantic import BaseModel, ConfigDict, Field


class FetchAPIRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(
        ...,
        min_length=1,
        description=(
            "Absolute `http://` or `https://` URL of an HTML page to render. "
            "Binary resources such as images, audio, video, archives, and PDFs "
            "are rejected with `not_html`; use the Files API for stored artifacts."
        ),
        examples=["https://example.com/"],
    )
    accept: str | None = Field(
        default=None,
        description=(
            "Requested output media type. `application/pdf` returns a PDF. "
            "`text/markdown`, `text/plain`, `text/*`, `*/*`, browser default "
            "headers, or an omitted header return Markdown. Other concrete media "
            "types such as `application/json` are rejected with HTTP 406."
        ),
        examples=["text/markdown", "application/pdf"],
    )
