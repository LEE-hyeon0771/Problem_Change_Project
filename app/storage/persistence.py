from __future__ import annotations

from typing import Protocol

from app.schemas.base import GenerateRequest, ProblemResponse
from app.schemas.storage import SavedProblemRecord
from app.storage.problem_store import LocalProblemStore


class DBProblemStore(Protocol):
    def save(self, record: SavedProblemRecord) -> int:
        ...


class ProblemPersistenceService:
    def __init__(
        self,
        *,
        local_store: LocalProblemStore,
        db_store: DBProblemStore | None = None,
    ) -> None:
        self.local_store = local_store
        self.db_store = db_store

    def persist(self, *, request: GenerateRequest, result: ProblemResponse) -> SavedProblemRecord:
        record = self.local_store.save(request=request, result=result)

        if self.db_store is not None:
            db_row_id = self.db_store.save(record)
            record.storage_meta.db_saved = True
            record.storage_meta.db_row_id = db_row_id
            self.local_store.overwrite(record)

        return record
