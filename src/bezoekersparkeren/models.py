from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from typing import List

class ParkingSession(BaseModel):
    id: Optional[str] = None
    plate: str
    active: bool
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class ScheduleRule(BaseModel):
    # Days of week: 0=Mon, 6=Sun
    days: List[int] 
    start_time: str # HH:MM
    end_time: str # HH:MM
    
class Zone(BaseModel):
    name: str # e.g. "Filmwijk"
    code: str # e.g. "36044"
    rules: List[ScheduleRule]
    hourly_rate: float
    max_daily_rate: float

class Balance(BaseModel):
    amount: float
    currency: str = "EUR"

class Favorite(BaseModel):
    plate: str
    name: Optional[str] = None
