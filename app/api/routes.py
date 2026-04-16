from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import generate_api_key, get_prefix_display, verify_api_key
from app.models.api_key import ApiKey
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyResponseWithSecret,
    VerifyRequest,
    VerifyResponse,
)

router = APIRouter()
settings = get_settings()


def verify_admin_key(authorization: str = Header(...)):
    """
    Middleware to ensure the parent application (PDFIvy) is the one calling these endpoints.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    if token != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin API key")

    return True


@router.post("/keys", response_model=ApiKeyResponseWithSecret)
async def create_api_key(
    req: ApiKeyCreate, db: AsyncSession = Depends(get_db), _=Depends(verify_admin_key)
):
    """
    Called by the parent application when a user wants to generate a new API key.
    """
    plain_text_key, hashed_key, public_id = generate_api_key(settings.KEY_PREFIX)
    display_prefix = get_prefix_display(plain_text_key)

    expires_at = None
    if req.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=req.expires_in_days)

    db_api_key = ApiKey(
        public_id=public_id,
        key_hash=hashed_key,
        prefix=display_prefix,
        user_id=req.user_id,
        name=req.name,
        scopes=req.scopes,
        expires_at=expires_at,
    )

    db.add(db_api_key)
    await db.commit()
    await db.refresh(db_api_key)

    return ApiKeyResponseWithSecret(
        id=db_api_key.id,
        name=db_api_key.name,
        prefix=db_api_key.prefix,
        key=plain_text_key,
        user_id=db_api_key.user_id,
        created_at=db_api_key.created_at,
    )


@router.get("/keys/{user_id}", response_model=List[ApiKeyResponse])
async def list_user_keys(
    user_id: str, db: AsyncSession = Depends(get_db), _=Depends(verify_admin_key)
):
    """
    Called by the parent application to list all active keys for a specific user.
    """
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id)
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return keys


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: str, db: AsyncSession = Depends(get_db), _=Depends(verify_admin_key)
):
    """
    Called by the parent application to permanently revoke an API key.
    """
    await db.execute(delete(ApiKey).where(ApiKey.id == key_id))
    await db.commit()


@router.post("/verify", response_model=VerifyResponse)
async def verify_key(req: VerifyRequest, db: AsyncSession = Depends(get_db)):
    """
    HIGH-SPEED ENDPOINT: Called constantly by the parent application to validate incoming MCP requests.
    Does NOT require the admin key (the incoming token IS what is being verified).
    """
    # 1. Check format and extract public_id
    # Format: mcp_sk_<public_id>_<secret>
    if not req.key or not req.key.startswith(settings.KEY_PREFIX):
        return VerifyResponse(valid=False, error="Invalid key format")

    parts = req.key[len(settings.KEY_PREFIX) :].split("_")
    if len(parts) != 2:
        return VerifyResponse(valid=False, error="Invalid key format")

    public_id = parts[0]

    # 2. Fast O(1) DB lookup
    result = await db.execute(
        select(ApiKey).where(ApiKey.public_id == public_id, ApiKey.is_active.is_(True))
    )
    db_key = result.scalar_one_or_none()

    if not db_key:
        return VerifyResponse(valid=False, error="Invalid API key")

    # 3. Cryptographic verification
    if not verify_api_key(req.key, db_key.key_hash):
        return VerifyResponse(valid=False, error="Invalid API key")

    # 4. Expiration check
    if db_key.expires_at and db_key.expires_at.replace(
        tzinfo=timezone.utc
    ) < datetime.now(timezone.utc):
        return VerifyResponse(valid=False, error="Key expired")

    # 5. Update last used (Note: In ultra-high scale, this would be queued/batched)
    db_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    return VerifyResponse(valid=True, user_id=db_key.user_id, scopes=db_key.scopes)
