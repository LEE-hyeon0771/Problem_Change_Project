from __future__ import annotations

import json
from pathlib import Path
from typing import cast, get_args

from app.core.errors import PersistenceError
from app.schemas.base import GenerateRequest, ProblemResponse
from app.schemas.storage import ProblemResult, ProblemType, SavedProblemRecord, build_passage_id


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

    @staticmethod
    def _attempt_filename(attempt_no: int) -> str:
        return f"attempt_{attempt_no:03d}.json"

    @staticmethod
    def _write_record(*, abs_path: Path, record: SavedProblemRecord, mode: str) -> None:
        with abs_path.open(mode, encoding="utf-8") as fp:
            json.dump(record.model_dump(mode="json"), fp, ensure_ascii=False, indent=2)
            fp.write("\n")
