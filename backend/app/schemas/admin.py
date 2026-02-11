from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    database: str
    openai: str
    timestamp: datetime
