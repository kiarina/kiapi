import uuid
from pathlib import Path

_NODE_ID_FILE = "node_id"


def get_or_create_node_id(data_dir: str | Path) -> str:
    """Return the persistent relay node ID stored under ``data_dir``.

    The ID is generated once and reused across restarts. Callers should hold the
    single-instance lock for ``data_dir`` before calling this so that concurrent
    processes never share the same node ID.
    """
    directory = Path(data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / _NODE_ID_FILE

    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value

    node_id = uuid.uuid4().hex[:12]
    path.write_text(f"{node_id}\n", encoding="utf-8")
    return node_id
