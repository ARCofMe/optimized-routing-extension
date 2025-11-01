from pydantic import BaseModel
from typing import Optional

class RouteConfig(BaseModel):
    start_location: Optional[str] = None
    end_location: Optional[str] = None
