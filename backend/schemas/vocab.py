from typing import Literal

from backend.schemas.base import ProblemResponse


class VocabResponse(ProblemResponse):
    type: Literal["vocab"] = "vocab"
