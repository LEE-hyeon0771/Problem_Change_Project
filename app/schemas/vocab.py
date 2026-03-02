from typing import Literal

from app.schemas.base import ProblemResponse


class VocabResponse(ProblemResponse):
    type: Literal["vocab"] = "vocab"
