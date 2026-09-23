from typing import Literal

from backend.schemas.base import ProblemResponse


class ReferenceResponse(ProblemResponse):
    type: Literal["reference"] = "reference"
