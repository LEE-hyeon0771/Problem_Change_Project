from typing import Literal

from backend.schemas.base import ProblemResponse


class IrrelevantResponse(ProblemResponse):
    type: Literal["irrelevant"] = "irrelevant"
