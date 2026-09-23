from typing import Literal

from backend.schemas.base import ProblemResponse


class SummaryResponse(ProblemResponse):
    type: Literal["summary"] = "summary"
