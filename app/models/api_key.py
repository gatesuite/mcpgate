from sqlalchemy import Column, String, DateTime, Boolean, JSON
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Fast O(1) lookup ID embedded in the plain text key
    public_id = Column(String, nullable=False, unique=True, index=True)
    
    # We only store the hash of the key, never the plain text
    key_hash = Column(String, nullable=False)
    
    # A recognizable prefix + partial key so users can identify it (e.g. mcp_sk_...1a2b)
    prefix = Column(String, nullable=False)
    
    # The ID of the user in the parent application (e.g. PDFIvy)
    user_id = Column(String, nullable=False, index=True)
    
    # Optional name given by the user (e.g. "Claude Desktop Key")
    name = Column(String, nullable=True)
    
    # Optional JSON object to store scopes or permissions (e.g. {"read": true, "write": false})
    scopes = Column(JSON, nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
