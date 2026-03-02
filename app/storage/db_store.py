from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.core.errors import PersistenceError
from app.db.models import Base, ProblemRecordEntity
from app.schemas.storage import SavedProblemRecord


class SQLAlchemyProblemStore:
    def __init__(self, *, database_url: str, echo: bool = False) -> None:
        if not database_url:
            raise PersistenceError("DATABASE_URL is required when DB persistence is enabled.")

        self.engine = create_engine(database_url, echo=echo, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        self._init_schema()

    def _init_schema(self) -> None:
        try:
            Base.metadata.create_all(self.engine)
        except SQLAlchemyError as exc:
            raise PersistenceError(f"Failed to initialize DB schema: {exc}") from exc

    def save(self, record: SavedProblemRecord) -> int:
        entity = ProblemRecordEntity(
            schema_version=record.schema_version,
            problem_uid=record.problem_uid,
            problem_type=record.problem_type,
            passage_id=record.passage_id,
            attempt_no=record.attempt_no,
            request_json=record.request.model_dump(mode="json"),
            result_json=record.result.model_dump(mode="json"),
            file_path=record.storage_meta.file_path,
            created_at=record.created_at,
        )

        try:
            with self.SessionLocal() as session:
                session.add(entity)
                session.commit()
                session.refresh(entity)
                return int(entity.id)
        except IntegrityError as exc:
            raise PersistenceError(f"DB insert conflict for problem record: {exc}") from exc
        except SQLAlchemyError as exc:
            raise PersistenceError(f"DB insert failed: {exc}") from exc
