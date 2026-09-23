from typing import Literal

from backend.schemas.base import ProblemResponse


class TitleResponse(ProblemResponse):
    type: Literal["title"] = "title"
