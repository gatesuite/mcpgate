from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


# Used when creating a new key
class ApiKeyCreate(BaseModel):
    user_id: str
    name: Optional[str] = None
    scopes: Optional[Dict[str, Any]] = None
    expires_in_days: Optional[int] = None


# Returned when a key is newly created (includes the full secret)
class ApiKeyResponseWithSecret(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: Optional[str]
    prefix: str
    key: str  # The actual plain-text key (only shown once)
    user_id: str
    created_at: datetime


# Returned for list operations (never includes the full secret)
class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: Optional[str]
    prefix: str
    user_id: str
    scopes: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]


# Payload sent by the parent application to verify an incoming API Key
class VerifyRequest(BaseModel):
    key: str


# Response back to the parent application after verification
class VerifyResponse(BaseModel):
    valid: bool
    user_id: Optional[str] = None
    scopes: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
