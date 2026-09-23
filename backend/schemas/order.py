from typing import Literal

from backend.schemas.base import ProblemResponse


class OrderResponse(ProblemResponse):
    type: Literal["order"] = "order"
