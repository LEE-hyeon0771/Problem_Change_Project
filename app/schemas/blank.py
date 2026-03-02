from typing import Literal

from app.schemas.base import ProblemResponse


class BlankResponse(ProblemResponse):
    type: Literal["blank"] = "blank"
