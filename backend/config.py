"""
Configuration module for Decision Authority.
Handles environment variables and Gemini API setup.

SECURITY: All sensitive values MUST come from environment variables.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""
    
    # ─────────────────────────────────────────────────────────────
    # SECURITY: API keys from environment only
    # ─────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-3-flash-preview"
    
    # ─────────────────────────────────────────────────────────────
    # DEBUG MODE: Controls error verbosity
    # Set to "true" in development, "false" (or unset) in production
    # ─────────────────────────────────────────────────────────────
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    # Timeouts
    GEMINI_TIMEOUT: int = 15  # seconds
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate required configuration.
        SECURITY: Fails hard if API key is missing - prevents running without auth.
        """
        if not cls.GEMINI_API_KEY:
            print("=" * 60)
            print("❌ FATAL: GEMINI_API_KEY is not configured!")
            print("")
            print("   To fix this:")
            print("   1. Create a .env file in the project root")
            print("   2. Add: GEMINI_API_KEY=your_api_key_here")
            print("   3. Get your key from: https://aistudio.google.com/app/apikey")
            print("=" * 60)
            return False
        return True
    
    @classmethod
    def get_masked_key(cls) -> str:
        """Return masked API key for safe logging."""
        if not cls.GEMINI_API_KEY or len(cls.GEMINI_API_KEY) < 8:
            return "NOT_SET"
        return f"...{cls.GEMINI_API_KEY[-4:]}"


# ─────────────────────────────────────────────────────────────
# SECURITY: Hard fail if API key is missing
# The server should NOT start without proper configuration
# ─────────────────────────────────────────────────────────────
if not Config.validate():
    print("\n🛑 Server startup aborted due to missing configuration.")
    sys.exit(1)
