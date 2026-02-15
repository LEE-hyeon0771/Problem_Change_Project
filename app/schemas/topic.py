from typing import Literal

from app.schemas.base import ProblemResponse


class TopicResponse(ProblemResponse):
    type: Literal["topic"] = "topic"
