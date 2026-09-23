from typing import Literal

from backend.schemas.base import ProblemResponse


class BlankResponse(ProblemResponse):
    type: Literal["blank"] = "blank"
