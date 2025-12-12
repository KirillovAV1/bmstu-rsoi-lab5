from typing import Union
from enum import Enum
from pydantic import BaseModel

class LoyaltyLevel(str, Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"


class LoyaltyInfoResponse(BaseModel):
    status: LoyaltyLevel
    discount: int
    reservationCount: int