from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import cast, get_args

from app.core.errors import PersistenceError
from app.schemas.base import GenerateRequest, ProblemResponse
from app.schemas.storage import ProblemResult, ProblemType, SavedProblemRecord, build_passage_id

logger = logging.getLogger(__name__)


class LocalProblemStore:
    def __init__(self, root_dir: str | Path = "app/problems") -> None:
        self.root_dir = Path(root_dir)

    def save(self, *, request: GenerateRequest, result: ProblemResponse) -> SavedProblemRecord:
        problem_type = result.type
        valid_types = get_args(ProblemType)
        if problem_type not in valid_types:
            raise PersistenceError(f"Unsupported problem type for persistence: {problem_type!r}")
        typed_problem_type = cast(ProblemType, problem_type)
        typed_result = cast(ProblemResult, result)

        passage_id = build_passage_id(request.passage)
        target_dir = self.root_dir / typed_problem_type / passage_id
        target_dir.mkdir(parents=True, exist_ok=True)

        max_attempt = 999_999
        for attempt_no in range(1, max_attempt + 1):
            filename = self._attempt_filename(attempt_no)
            abs_path = target_dir / filename
            rel_path = (Path("app/problems") / typed_problem_type / passage_id / filename).as_posix()

            try:
                record = SavedProblemRecord.from_generation(
                    problem_type=typed_problem_type,
                    attempt_no=attempt_no,
                    request=request,
                    result=typed_result,
                    file_path=rel_path,
                )
            except Exception as exc:
                raise PersistenceError(f"Failed to build saved problem payload: {exc}") from exc

            try:
                self._write_record(abs_path=abs_path, record=record, mode="x")
                return record
            except FileExistsError:
                continue
            except OSError as exc:
                raise PersistenceError(f"Failed to write problem file '{abs_path}': {exc}") from exc

        raise PersistenceError(
            f"Failed to allocate attempt number for type='{typed_problem_type}' and passage_id='{passage_id}'."
        )

    def overwrite(self, record: SavedProblemRecord) -> None:
        abs_path = self.root_dir / record.problem_type / record.passage_id / self._attempt_filename(record.attempt_no)
        try:
            self._write_record(abs_path=abs_path, record=record, mode="w")
        except OSError as exc:
            raise PersistenceError(f"Failed to update problem file '{abs_path}': {exc}") from exc

    def list_records(self, *, problem_type: str | None = None, limit: int = 100) -> list[SavedProblemRecord]:
        valid_types = set(get_args(ProblemType))
        if problem_type is not None and problem_type not in valid_types:
            raise PersistenceError(f"Unsupported problem type for listing: {problem_type!r}")

        type_dirs = [self.root_dir / problem_type] if problem_type else [self.root_dir / kind for kind in valid_types]
        records: list[SavedProblemRecord] = []
        for type_dir in type_dirs:
            if not type_dir.exists():
                continue
            for path in type_dir.glob("*/attempt_*.json"):
                try:
                    records.append(self._read_record(path))
                except Exception as exc:
                    logger.warning("Skipping invalid problem record '%s': %s", path, exc)

        records.sort(key=lambda record: (record.created_at, record.attempt_no, record.problem_uid), reverse=True)
        return records[:limit]

    def get_record(self, problem_uid: str) -> SavedProblemRecord | None:
        for path in self.root_dir.glob("*/" + "[a-f0-9]" * 16 + "/attempt_*.json"):
            try:
                record = self._read_record(path)
            except Exception as exc:
                logger.warning("Skipping invalid problem record '%s': %s", path, exc)
                continue
            if record.problem_uid == problem_uid:
                return record
        return None

    @staticmethod
    def _attempt_filename(attempt_no: int) -> str:
        return f"attempt_{attempt_no:03d}.json"

    @staticmethod
    def _write_record(*, abs_path: Path, record: SavedProblemRecord, mode: str) -> None:
        with abs_path.open(mode, encoding="utf-8") as fp:
            json.dump(record.model_dump(mode="json"), fp, ensure_ascii=False, indent=2)
            fp.write("\n")

    @staticmethod
    def _read_record(path: Path) -> SavedProblemRecord:
        with path.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
        return SavedProblemRecord.model_validate(payload)
