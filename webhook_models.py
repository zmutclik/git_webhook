from pydantic import BaseModel
from typing import Optional, Dict, Any


# Pydantic models
class WebhookResponse(BaseModel):
    status: str
    message: str
    timestamp: str
    output: Optional[str] = None
    error: Optional[str] = None


class StatusResponse(BaseModel):
    status: str
    timestamp: str
    config: Dict[str, Any]


class ManualPullResponse(BaseModel):
    status: str
    message: str
    output: Optional[str] = None
    error: Optional[str] = None
