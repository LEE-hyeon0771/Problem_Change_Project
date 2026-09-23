from typing import Literal

from backend.schemas.base import ProblemResponse


class GrammarResponse(ProblemResponse):
    type: Literal["grammar"] = "grammar"
