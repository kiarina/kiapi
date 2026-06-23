from kiapi.capabilities.web._operations.resolve_search_params import (
    resolve_search_params,
)
from kiapi.capabilities.web._settings import WebSettings
from kiapi.capabilities.web._views.search_request import SearchRequest


def test_resolve_search_params_preserves_request_values() -> None:
    settings = WebSettings()
    req = SearchRequest.model_validate(
        {
            "query": "mlx quantization",
            "categories": ["it", "science"],
            "engines": ["google", "duckduckgo"],
            "language": "en",
            "time_range": "month",
            "safesearch": 1,
            "page": 2,
            "max_results": 7,
        }
    )

    params = resolve_search_params(settings, req)

    assert params.query == "mlx quantization"
    # lists are comma-joined into SearXNG's wire form
    assert params.categories == "it,science"
    assert params.engines == "google,duckduckgo"
    assert params.language == "en"
    assert params.time_range == "month"
    assert params.safesearch == 1
    assert params.pageno == 2
    assert params.max_results == 7


def test_resolve_search_params_falls_back_to_settings_defaults() -> None:
    settings = WebSettings(
        default_categories=["general"],
        default_engines=["bing"],
        default_language="ja",
        default_safesearch=2,
        default_max_results=5,
    )
    req = SearchRequest.model_validate({"query": "apple"})

    params = resolve_search_params(settings, req)

    assert params.categories == "general"
    assert params.engines == "bing"
    assert params.language == "ja"
    assert params.safesearch == 2
    assert params.pageno == 1
    assert params.max_results == 5
    assert params.time_range is None


def test_resolve_search_params_none_categories_omit_the_param() -> None:
    settings = WebSettings()  # all defaults None except max_results
    req = SearchRequest.model_validate({"query": "apple"})

    params = resolve_search_params(settings, req)

    assert params.categories is None
    assert params.engines is None
    # format=json is forced; absent optional params stay out of the querystring
    qp = params.query_params()
    assert qp["q"] == "apple"
    assert qp["format"] == "json"
    assert qp["pageno"] == 1
    assert "categories" not in qp
    assert "language" not in qp


def test_query_params_includes_set_fields() -> None:
    settings = WebSettings()
    req = SearchRequest.model_validate(
        {
            "query": "x",
            "categories": ["it"],
            "language": "en",
            "safesearch": 0,
            "time_range": "day",
        }
    )

    qp = resolve_search_params(settings, req).query_params()

    assert qp["categories"] == "it"
    assert qp["language"] == "en"
    assert qp["safesearch"] == 0
    assert qp["time_range"] == "day"
