from typing import Literal

from app.schemas.base import ProblemResponse


class TitleResponse(ProblemResponse):
    type: Literal["title"] = "title"
