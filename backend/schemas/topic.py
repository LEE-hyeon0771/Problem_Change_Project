from typing import Literal

from backend.schemas.base import ProblemResponse


class TopicResponse(ProblemResponse):
    type: Literal["topic"] = "topic"
