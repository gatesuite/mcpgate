import secrets
import hashlib
import bcrypt


def _prehash(key: str) -> str:
    """Pre-hash with SHA256 to ensure the length is always 64 chars."""
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

def generate_api_key(prefix: str = "mcp_sk_") -> tuple[str, str, str]:
    """
    Generates a secure random API key and its hash.
    Embeds a public ID in the key for fast O(1) DB lookups.
    Format: mcp_sk_<public_id>_<secret>
    Returns: (plain_text_key, hashed_key, public_id)
    """
    public_id = secrets.token_urlsafe(8)  # ~11 chars
    secret = secrets.token_urlsafe(32)    # ~43 chars
    
    plain_text_key = f"{prefix}{public_id}_{secret}"

    salt = bcrypt.gensalt()
    hashed_key_bytes = bcrypt.hashpw(plain_text_key.encode('utf-8'), salt)
    hashed_key = hashed_key_bytes.decode('utf-8')

    return plain_text_key, hashed_key, public_id

def verify_api_key(plain_text_key: str, hashed_key: str) -> bool:
    """Verify a plain text key against a bcrypt hash."""
    return bcrypt.checkpw(plain_text_key.encode('utf-8'), hashed_key.encode('utf-8'))

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
