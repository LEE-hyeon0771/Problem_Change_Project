from typing import Literal

from app.schemas.base import ProblemResponse


class InsertionResponse(ProblemResponse):
    type: Literal["insertion"] = "insertion"
