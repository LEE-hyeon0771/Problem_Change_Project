from typing import Literal

from app.schemas.base import ProblemResponse


class ImplicitResponse(ProblemResponse):
    type: Literal["implicit"] = "implicit"
