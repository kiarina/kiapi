import uuid


def new_relay_session_id() -> str:
    return f"session-{uuid.uuid4().hex}"
