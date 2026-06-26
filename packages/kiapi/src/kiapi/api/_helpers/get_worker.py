from fastapi import Request

from kiapi.core.worker import Worker


def get_worker(request: Request) -> Worker:
    return request.app.state.worker  # type: ignore
