from typing import Literal

from app.schemas.base import ProblemResponse


class SummaryResponse(ProblemResponse):
    type: Literal["summary"] = "summary"
