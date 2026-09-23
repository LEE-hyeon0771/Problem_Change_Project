from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProblemRecordEntity(Base):
    __tablename__ = "problem_records"
    __table_args__ = (
        UniqueConstraint("problem_uid", name="uq_problem_records_problem_uid"),
        UniqueConstraint("problem_type", "passage_id", "attempt_no", name="uq_problem_records_attempt"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    problem_uid: Mapped[str] = mapped_column(String(32), nullable=False)
    problem_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    passage_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    request_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
