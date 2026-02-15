from typing import Literal

from app.schemas.base import ProblemResponse


class IrrelevantResponse(ProblemResponse):
    type: Literal["irrelevant"] = "irrelevant"
