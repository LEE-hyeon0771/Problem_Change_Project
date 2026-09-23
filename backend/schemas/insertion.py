from typing import Literal

from backend.schemas.base import ProblemResponse


class InsertionResponse(ProblemResponse):
    type: Literal["insertion"] = "insertion"
