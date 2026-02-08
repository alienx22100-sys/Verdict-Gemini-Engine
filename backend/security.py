"""
Security utilities for Decision Authority.
Input validation, sanitization, and prompt injection prevention.
"""

import re
from typing import Tuple

# ─────────────────────────────────────────────────────────────
# SECURITY CONSTANTS
# ─────────────────────────────────────────────────────────────

# Maximum allowed input length (prevents abuse and excessive API costs)
MAX_INPUT_LENGTH = 2000

# Minimum meaningful input length
MIN_INPUT_LENGTH = 10

# Patterns that may indicate prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"you\s+are\s+now",
    r"act\s+as\s+if",
    r"pretend\s+(you\s+are|to\s+be)",
    r"new\s+instructions:",
    r"system\s*:",
    r"<\s*system\s*>",
    r"\[\s*SYSTEM\s*\]",
]

# Compile patterns for efficiency
COMPILED_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS
]


# ─────────────────────────────────────────────────────────────
# INPUT VALIDATION
# ─────────────────────────────────────────────────────────────

def validate_input(text: str) -> Tuple[bool, str]:
    """
    Validate user input for security and sanity.
    
    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is empty string.
    """
    if not text:
        return False, "Input cannot be empty."
    
    # Strip whitespace for length check
    stripped = text.strip()
    
    if len(stripped) < MIN_INPUT_LENGTH:
        return False, f"Input too short. Please provide at least {MIN_INPUT_LENGTH} characters."
    
    if len(stripped) > MAX_INPUT_LENGTH:
        return False, f"Input too long. Maximum {MAX_INPUT_LENGTH} characters allowed."
    
    # Check for prompt injection patterns
    for pattern in COMPILED_INJECTION_PATTERNS:
        if pattern.search(stripped):
            return False, "Input contains disallowed patterns. Please rephrase your decision."
    
    return True, ""


# ─────────────────────────────────────────────────────────────
# INPUT SANITIZATION
# ─────────────────────────────────────────────────────────────

def sanitize_input(text: str) -> str:
    """
    Sanitize user input before passing to AI prompts.
    Does NOT modify the semantic content, only removes dangerous patterns.
    
    Security measures:
    1. Normalize whitespace
    2. Remove null bytes and control characters
    3. Limit consecutive special characters
    """
    if not text:
        return ""
    
    # Remove null bytes and most control characters (keep newlines, tabs)
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Normalize excessive whitespace (but preserve paragraph breaks)
    sanitized = re.sub(r'[ \t]+', ' ', sanitized)  # Multiple spaces/tabs to single space
    sanitized = re.sub(r'\n{3,}', '\n\n', sanitized)  # Max 2 consecutive newlines
    
    # Strip leading/trailing whitespace
    sanitized = sanitized.strip()
    
    return sanitized


# ─────────────────────────────────────────────────────────────
# SECURITY HELPERS
# ─────────────────────────────────────────────────────────────

def mask_api_key(key: str) -> str:
    """Mask API key for safe logging. Shows only last 4 characters."""
    if not key or len(key) < 8:
        return "***"
    return f"...{key[-4:]}"
