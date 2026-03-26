import secrets
import string
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_api_key(prefix: str = "mcp_sk_") -> tuple[str, str, str]:
    """
    Generates a secure random API key and its hash.
    Embeds a public ID in the key for fast O(1) DB lookups.
    Format: mcp_sk_<public_id>_<secret>
    Returns: (plain_text_key, hashed_key, public_id)
    """
    public_id = secrets.token_urlsafe(8)  # 11 chars
    secret = secrets.token_urlsafe(32)    # 43 chars
    
    plain_text_key = f"{prefix}{public_id}_{secret}"
    
    # We only hash the secret part, or the whole thing. Let's hash the whole thing for simplicity
    hashed_key = pwd_context.hash(plain_text_key)
    
    return plain_text_key, hashed_key, public_id

def verify_api_key(plain_text_key: str, hashed_key: str) -> bool:
    """
    Verifies a plain text key against a hash.
    """
    return pwd_context.verify(plain_text_key, hashed_key)

def get_prefix_display(plain_text_key: str) -> str:
    """
    Returns a safe display string like: mcp_sk_...1a2b
    """
    parts = plain_text_key.split("_")
    if len(parts) >= 3:
        # It has our standard prefix
        prefix_part = "_".join(parts[:-1]) + "_"
        secret_part = parts[-1]
        return f"{prefix_part}...{secret_part[-4:]}"
    
    return f"...{plain_text_key[-4:]}"
