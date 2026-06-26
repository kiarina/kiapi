from typing import Any, cast

from fastapi.testclient import TestClient

from kiapi.api import build_openapi
from kiapi.api.app import app
from kiapi.cli import register_all_capabilities
from kiapi.core.capability import capability_spec_registry

register_all_capabilities()

client = TestClient(app)


def test_root_openapi_documents_common_paths_and_capability_links() -> None:
    schema = app.openapi()

    assert sorted(schema["paths"]) == [
        "/health",
        "/v1/files",
        "/v1/files/{file_id}",
        "/v1/files/{file_id}/download",
        "/v1/jobs",
        "/v1/jobs/{job_id}",
    ]
    assert "/v1/chat/completions" not in schema["paths"]
    assert "x-kiapi-capabilities" not in schema
    description = schema["info"]["description"]
    assert "Generate images and train LoRA adapters with Z-Image models." in description
    assert "Generate video from text, image, and music or audio inputs." in description
    domain_positions = [
        description.index(f"- **{domain}**")
        for domain in ("chat", "embedding", "image", "audio", "video", "web")
    ]
    assert domain_positions == sorted(domain_positions)
    assert description.index("kiapi Chat API") < description.index(
        "kiapi Embedding API"
    )
    assert description.index("kiapi Z-Image API") < description.index(
        "kiapi ACE-Step API"
    )
    assert "[Swagger UI](/v1/image/zimage/docs)" in description
    assert "[ReDoc](/v1/image/zimage/redoc)" in description
    assert "[OpenAPI JSON](/v1/image/zimage/openapi.json)" in description
    assert "/docs" not in schema["paths"]


def test_file_ref_schema_is_discriminated_union() -> None:
    schema = _capability_schema("zimage")

    file_ref = schema["components"]["schemas"]["FileRef"]

    assert file_ref["discriminator"]["propertyName"] == "type"
    assert file_ref["discriminator"]["mapping"] == {
        "data_url": "#/components/schemas/FileDataURLRef",
        "file_id": "#/components/schemas/FileIDRef",
        "url": "#/components/schemas/FileURLRef",
    }
    assert [ref["$ref"] for ref in file_ref["oneOf"]] == [
        "#/components/schemas/FileIDRef",
        "#/components/schemas/FileURLRef",
        "#/components/schemas/FileDataURLRef",
    ]


def test_generation_routes_document_json_request_and_job_or_raw_response() -> None:
    routes = [
        ("acestep", "/v1/audio/acestep/cover", "audio/wav"),
        ("audiogen", "/v1/audio/audiogen/generate", "audio/wav"),
        ("qwen", "/v1/image/qwen/generate", "image/png"),
        ("ltx2", "/v1/video/ltx2/generate", "video/mp4"),
    ]

    for capability, path, raw_media_type in routes:
        schema = _capability_schema(capability)
        operation = schema["paths"][path]["post"]

        assert set(operation["requestBody"]["content"]) == {"application/json"}
        assert _parameter(operation, "Accept", "header") is not None
        assert "application/json" in operation["responses"]["200"]["content"]
        assert raw_media_type in operation["responses"]["200"]["content"]
        assert "application/json" in operation["responses"]["202"]["content"]


def test_core_body_routes_document_pydantic_request_models() -> None:
    routes = [
        ("chat", "/v1/chat/completions", "ChatRequest"),
        ("embedding", "/v1/embedding", "EmbedRequest"),
        ("web", "/v1/web/search", "SearchRequest"),
    ]

    for capability, path, schema_name in routes:
        schema = _capability_schema(capability)
        operation = schema["paths"][path]["post"]
        json_body = operation["requestBody"]["content"]["application/json"]

        assert json_body["schema"]["$ref"] == f"#/components/schemas/{schema_name}"


def test_web_fetch_documents_query_and_accept_header() -> None:
    schema = _capability_schema("web")
    operation = schema["paths"]["/v1/web/fetch"]["get"]

    url = _parameter(operation, "url", "query")
    accept = _parameter(operation, "Accept", "header")

    assert url is not None
    assert url["required"] is True
    assert url["schema"]["minLength"] == 1
    assert "Non-HTML" in url["description"]
    assert accept is not None
    assert accept["required"] is False
    assert "application/pdf" in accept["description"]


def test_web_openapi_documents_search_schema() -> None:
    schema = _capability_schema("web")
    operation = schema["paths"]["/v1/web/search"]["post"]

    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    description = operation["description"]

    assert request_schema["$ref"] == "#/components/schemas/SearchRequest"
    assert response_schema["$ref"] == "#/components/schemas/SearchResponse"
    assert "SearXNG inline operators" in description

    search_request = schema["components"]["schemas"]["SearchRequest"]
    assert "site:github.com" in search_request["properties"]["query"]["description"]
    assert "general" in search_request["properties"]["categories"]["description"]
    assert search_request["properties"]["time_range"]["anyOf"][0]["enum"] == [
        "day",
        "week",
        "month",
        "year",
    ]
    assert search_request["properties"]["safesearch"]["anyOf"][0]["enum"] == [
        0,
        1,
        2,
    ]

    search_response = schema["components"]["schemas"]["SearchResponse"]
    assert (
        "Common keys include" in search_response["properties"]["results"]["description"]
    )
    assert (
        "unresponsive"
        in search_response["properties"]["unresponsive_engines"]["description"]
    )


def test_web_openapi_documents_fetch_raw_responses() -> None:
    schema = _capability_schema("web")
    operation = schema["paths"]["/v1/web/fetch"]["get"]
    response_200 = operation["responses"]["200"]

    assert "text/markdown" in response_200["content"]
    assert "application/pdf" in response_200["content"]
    assert response_200["content"]["application/pdf"]["schema"]["format"] == "binary"
    assert "X-Kiapi-File-Id" in response_200["headers"]
    assert "X-Kiapi-Content-Type" in response_200["headers"]
    assert (
        operation["responses"]["406"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/FetchErrorResponse"
    )
    assert (
        operation["responses"]["422"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/FetchErrorResponse"
    )


def test_web_description_keeps_family_level_material() -> None:
    schema = _capability_schema("web")
    description = schema["info"]["description"]

    assert "When To Use" in description
    assert "Search Tips" in description
    assert "Fetch Tips" in description
    assert "## Params" not in description
    assert "## Fetch Params" not in description


def test_path_routes_document_typed_identifiers() -> None:
    schema = app.openapi()

    routes = [
        ("/v1/files/{file_id}", "get", "file_id", "^file_[0-9a-f]+$"),
        ("/v1/jobs/{job_id}", "get", "job_id", "^job_[0-9a-f]+$"),
    ]

    for path, method, name, pattern in routes:
        operation = schema["paths"][path][method]
        parameter = _parameter(operation, name, "path")

        assert parameter is not None
        assert parameter["required"] is True
        if pattern is not None:
            assert parameter["schema"]["pattern"] == pattern


def test_files_upload_remains_multipart() -> None:
    schema = app.openapi()

    operation = schema["paths"]["/v1/files"]["post"]

    assert "multipart/form-data" in operation["requestBody"]["content"]


def test_chat_openapi_includes_openai_compatible_models_endpoint() -> None:
    schema = _capability_schema("chat")

    assert sorted(schema["paths"]) == [
        "/v1/chat/completions",
        "/v1/chat/models",
        "/v1/models",
    ]
    assert schema["x-kiapi-capability"] == "chat"
    assert schema["x-kiapi-domain"] == "chat"


def test_zimage_openapi_is_limited_to_zimage_paths() -> None:
    schema = _capability_schema("zimage")

    assert sorted(schema["paths"]) == [
        "/v1/image/zimage/generate",
        "/v1/image/zimage/models",
        "/v1/image/zimage/train",
    ]
    assert "/v1/image/qwen/generate" not in schema["paths"]


def test_capability_model_list_uses_public_model_schema() -> None:
    response = client.get("/v1/image/zimage/models")

    assert response.status_code == 200
    model = response.json()[0]
    assert set(model) == {
        "name",
        "family",
        "domain",
        "aliases",
        "default",
        "features",
    }
    assert model["family"] == "zimage"
    assert model["domain"] == "image"


def test_capability_openapi_excludes_internal_model_spec_schema() -> None:
    schema = _capability_schema("zimage")
    schemas = schema["components"]["schemas"]
    response_schema = schema["paths"]["/v1/image/zimage/models"]["get"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"]

    assert response_schema["items"]["$ref"] == (
        "#/components/schemas/CapabilityModelSpec"
    )
    assert "ModelSpec" not in schemas
    public_properties = schemas["CapabilityModelSpec"]["properties"]
    assert "setup_resources" not in public_properties
    assert "weight_gb" not in public_properties
    assert "peak_headroom_gb" not in public_properties
    assert "framework" not in public_properties


def test_capability_openapi_includes_detailed_markdown_description() -> None:
    schema = _capability_schema("zimage")
    description = schema["info"]["description"]

    assert "Fast text-to-image generation and LoRA training" in description
    assert "## Performance" in description
    assert "## LoRA workflow" in description
    assert "turbo" in description


def test_docs_endpoints_render_swagger_ui_for_selected_openapi() -> None:
    routes = [
        ("/docs", "/openapi.json", "kiapi Common API"),
        ("/v1/chat/docs", "/v1/chat/openapi.json", "kiapi Chat API"),
        (
            "/v1/image/zimage/docs",
            "/v1/image/zimage/openapi.json",
            "kiapi Z-Image API",
        ),
    ]

    for docs_path, openapi_path, title in routes:
        response = client.get(docs_path)

        assert response.status_code == 200
        assert openapi_path in response.text
        assert title in response.text


def test_docs_endpoints_are_not_in_openapi_documents() -> None:
    root_schema = app.openapi()
    zimage_schema = _capability_schema("zimage")

    assert "/docs" not in root_schema["paths"]
    assert "/v1/image/zimage/docs" not in zimage_schema["paths"]
    assert "/v1/image/zimage/openapi.json" not in zimage_schema["paths"]


def test_redoc_endpoints_render_redoc_for_selected_openapi() -> None:
    routes = [
        ("/redoc", "/openapi.json", "kiapi Common API"),
        ("/v1/chat/redoc", "/v1/chat/openapi.json", "kiapi Chat API"),
        (
            "/v1/image/zimage/redoc",
            "/v1/image/zimage/openapi.json",
            "kiapi Z-Image API",
        ),
    ]

    for redoc_path, openapi_path, title in routes:
        response = client.get(redoc_path)

        assert response.status_code == 200
        assert openapi_path in response.text
        assert title in response.text


def test_redoc_endpoints_are_not_in_openapi_documents() -> None:
    root_schema = app.openapi()
    zimage_schema = _capability_schema("zimage")

    assert "/redoc" not in root_schema["paths"]
    assert "/v1/image/zimage/redoc" not in zimage_schema["paths"]


def _parameter(
    operation: dict[str, Any], name: str, location: str
) -> dict[str, Any] | None:
    for parameter in operation.get("parameters", []):
        if parameter["name"] == name and parameter["in"] == location:
            return cast(dict[str, Any], parameter)
    return None


def _capability_schema(name: str) -> dict[str, Any]:
    spec = capability_spec_registry.get(name)
    if spec is None:
        raise RuntimeError(f"kiapi capability {name!r} is not registered")
    return build_openapi(
        app,
        title=spec.title,
        description=spec.description,
        path_prefixes=spec.path_prefixes,
        include_paths=spec.include_paths,
        capability=spec,
    )
