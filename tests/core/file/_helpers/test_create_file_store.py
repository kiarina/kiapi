from kiapi.core.file import create_file_store


def test_create_file_store() -> None:
    file_store = create_file_store()
    print(file_store)
    assert True
