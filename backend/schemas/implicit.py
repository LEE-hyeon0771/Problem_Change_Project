from typing import Literal

from backend.schemas.base import ProblemResponse


class ImplicitResponse(ProblemResponse):
    type: Literal["implicit"] = "implicit"
