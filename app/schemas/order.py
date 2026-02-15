from typing import Literal

from app.schemas.base import ProblemResponse


class OrderResponse(ProblemResponse):
    type: Literal["order"] = "order"
