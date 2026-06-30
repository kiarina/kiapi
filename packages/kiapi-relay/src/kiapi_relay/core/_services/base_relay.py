from .._types.relay import Relay
from .._types.relay_name import RelayName


class BaseRelay(Relay):
    def __init__(self) -> None:
        self._name: RelayName | None = None
        self._node_id: str | None = None

    @property
    def name(self) -> RelayName:
        if self._name is None:
            raise ValueError("name is not set")
        return self._name

    @name.setter
    def name(self, value: RelayName) -> None:
        self._name = value

    @property
    def node_id(self) -> str:
        if self._node_id is None:
            raise ValueError("node_id is not set")
        return self._node_id

    @node_id.setter
    def node_id(self, value: str) -> None:
        self._node_id = value
