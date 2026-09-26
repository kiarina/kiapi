from pydantic import BaseModel, Field


class SearchOptions(BaseModel):
    """Choices currently enabled by the resident SearXNG instance."""

    categories: list[str] = Field(
        title="Categories", description="SearXNG's current search categories."
    )
    engines: list[str] = Field(
        title="Engines", description="SearXNG's currently enabled engines."
    )
