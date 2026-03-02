from typing import Literal

from app.schemas.base import ProblemResponse


class ReferenceResponse(ProblemResponse):
    type: Literal["reference"] = "reference"
