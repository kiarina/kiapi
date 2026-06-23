from kiapi.core.app import AppContext


def test_app_context() -> None:
    app_context = AppContext.create()
    print(app_context)
    assert True
