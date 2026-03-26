from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "MCPGate"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str
    
    # Security
    # This prefix is prepended to all generated keys (e.g. mcp_sk_...)
    KEY_PREFIX: str = "mcp_sk_"
    
    # The master token used by the main application (e.g. PDFIvy) to create/revoke keys for its users
    ADMIN_API_KEY: str

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
