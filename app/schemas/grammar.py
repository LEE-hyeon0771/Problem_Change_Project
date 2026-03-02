from typing import Literal

from app.schemas.base import ProblemResponse


class GrammarResponse(ProblemResponse):
    type: Literal["grammar"] = "grammar"
