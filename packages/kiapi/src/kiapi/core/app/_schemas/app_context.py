from dataclasses import dataclass
from typing import Self

from kiapi.core.file import FileStore, create_file_store
from kiapi.core.job import JobStore
from kiapi.core.memory import MemoryManager, create_memory_manager
from kiapi.core.model import ModelSpec
from kiapi.core.setup import SetupManager


@dataclass
class AppContext:
    memory_manager: MemoryManager
    job_store: JobStore
    file_store: FileStore
    setup_manager: SetupManager

    @classmethod
    def create(cls) -> Self:
        return cls(
            memory_manager=create_memory_manager(),
            job_store=JobStore(),
            file_store=create_file_store(),
            setup_manager=SetupManager(),
        )

    def ensure_model_ready(self, spec: ModelSpec) -> None:
        self.setup_manager.ensure_ready(spec)
