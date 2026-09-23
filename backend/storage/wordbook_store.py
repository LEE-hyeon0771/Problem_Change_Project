from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.core.errors import PersistenceError
from backend.schemas.storage import build_passage_id
from backend.schemas.wordbook import WordbookRequest, WordbookResponse
from backend.schemas.wordbook_storage import SavedWordbookRecord

logger = logging.getLogger(__name__)


class LocalWordbookStore:
    """단어장을 `backend/wordbooks/{passage_id}/attempt_{n}.json`으로 보관합니다.

    문항 저장소(`LocalProblemStore`)와 같은 규칙을 쓰지만 유형 디렉터리가 없습니다.
    단어장은 유형 구분이 없기 때문입니다.
    """

    def __init__(self, root_dir: str | Path = "backend/wordbooks") -> None:
        self.root_dir = Path(root_dir)

    def save(
        self,
        *,
        request: WordbookRequest,
        result: WordbookResponse,
        title: str = "",
    ) -> SavedWordbookRecord:
        passage_id = build_passage_id(request.passage)
        target_dir = self.root_dir / passage_id
        target_dir.mkdir(parents=True, exist_ok=True)

        max_attempt = 999_999
        for attempt_no in range(1, max_attempt + 1):
            filename = self._attempt_filename(attempt_no)
            abs_path = target_dir / filename
            rel_path = (Path("backend/wordbooks") / passage_id / filename).as_posix()

            try:
                record = SavedWordbookRecord.from_generation(
                    attempt_no=attempt_no,
                    request=request,
                    result=result,
                    file_path=rel_path,
                    title=title,
                )
            except Exception as exc:
                raise PersistenceError(f"Failed to build saved wordbook payload: {exc}") from exc

            try:
                self._write_record(abs_path=abs_path, record=record, mode="x")
                return record
            except FileExistsError:
                continue
            except OSError as exc:
                raise PersistenceError(f"Failed to write wordbook file '{abs_path}': {exc}") from exc

        raise PersistenceError(f"Failed to allocate attempt number for passage_id='{passage_id}'.")

    def list_records(self, *, limit: int = 100) -> list[SavedWordbookRecord]:
        records: list[SavedWordbookRecord] = []
        if not self.root_dir.exists():
            return records

        for path in self.root_dir.glob("*/attempt_*.json"):
            try:
                records.append(self._read_record(path))
            except Exception as exc:
                logger.warning("Skipping invalid wordbook record '%s': %s", path, exc)

        records.sort(key=lambda record: (record.created_at, record.attempt_no, record.wordbook_uid), reverse=True)
        return records[:limit]

    def get_record(self, wordbook_uid: str) -> SavedWordbookRecord | None:
        for path in self.root_dir.glob("*/attempt_*.json"):
            try:
                record = self._read_record(path)
            except Exception as exc:
                logger.warning("Skipping invalid wordbook record '%s': %s", path, exc)
                continue
            if record.wordbook_uid == wordbook_uid:
                return record
        return None

    def delete_record(self, wordbook_uid: str) -> bool:
        record = self.get_record(wordbook_uid)
        if record is None:
            return False

        abs_path = self.root_dir / record.passage_id / self._attempt_filename(record.attempt_no)
        try:
            abs_path.unlink(missing_ok=True)
        except OSError as exc:
            raise PersistenceError(f"Failed to delete wordbook file '{abs_path}': {exc}") from exc
        return True

    @staticmethod
    def _attempt_filename(attempt_no: int) -> str:
        return f"attempt_{attempt_no:03d}.json"

    @staticmethod
    def _write_record(*, abs_path: Path, record: SavedWordbookRecord, mode: str) -> None:
        with abs_path.open(mode, encoding="utf-8") as fp:
            json.dump(record.model_dump(mode="json"), fp, ensure_ascii=False, indent=2)
            fp.write("\n")

    @staticmethod
    def _read_record(path: Path) -> SavedWordbookRecord:
        with path.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
        return SavedWordbookRecord.model_validate(payload)
