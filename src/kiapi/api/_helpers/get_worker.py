from starlette.requests import HTTPConnection

from kiapi.core.worker import Worker


def get_worker(request: HTTPConnection) -> Worker:
    return request.app.state.worker  # type: ignore
