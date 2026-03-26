from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

# Used when creating a new key
class ApiKeyCreate(BaseModel):
    user_id: str
    name: Optional[str] = None
    scopes: Optional[Dict[str, Any]] = None
    expires_in_days: Optional[int] = None

# Returned when a key is newly created (includes the full secret)
class ApiKeyResponseWithSecret(BaseModel):
    id: str
    name: Optional[str]
    prefix: str
    key: str  # The actual plain-text key (only shown once)
    user_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Returned for list operations (never includes the full secret)
class ApiKeyResponse(BaseModel):
    id: str
    name: Optional[str]
    prefix: str
    user_id: str
    scopes: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True

# Payload sent by the parent application to verify an incoming API Key
class VerifyRequest(BaseModel):
    key: str

# Response back to the parent application after verification
class VerifyResponse(BaseModel):
    valid: bool
    user_id: Optional[str] = None
    scopes: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
