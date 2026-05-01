"""
Security service for the Election Assistant.
Scans user input for Sensitive Personal Information (PII)
and validates request data to prevent malicious input.
"""
import re
from typing import Tuple, Optional


# Compiled regex patterns for efficiency (pre-compiled at module load)
_SSN_PATTERN = re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b')
_AADHAAR_PATTERN = re.compile(r'\b\d{4}[\s]?\d{4}[\s]?\d{4}\b')
_CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d[ -]?){13,16}\b')

_PII_WARNING = (
    "WARNING: Please do not share sensitive personal information like your SSN, "
    "Aadhaar, or passwords. I am a secure assistant and do not need this data to help you."
)

_PII_KEYWORDS = frozenset(["ssn", "aadhaar", "password", "credit card", "debit card", "cvv", "pin"])


def scan_for_pii(text: str) -> Tuple[bool, Optional[str]]:
    """
    Scans the input text for Sensitive Personal Information (PII).

    Checks for:
    - Sensitive keyword patterns (SSN, Aadhaar, password, etc.)
    - Structural patterns like numeric sequences matching SSN/Aadhaar formats

    Args:
        text: The user-provided input string to scan.

    Returns:
        A tuple (has_pii, warning_message):
            - has_pii (bool): True if PII is detected, False otherwise.
            - warning_message (str | None): Warning string if PII found, else None.
    """
    if not text or not text.strip():
        return False, None

    query_lower = text.lower()

    # Keyword check (O(1) per keyword via frozenset)
    for keyword in _PII_KEYWORDS:
        if keyword in query_lower:
            return True, _PII_WARNING

    # Structural pattern checks (regex)
    if _SSN_PATTERN.search(text):
        return True, _PII_WARNING

    if _AADHAAR_PATTERN.search(text):
        return True, _PII_WARNING

    return False, None


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitizes user input by stripping leading/trailing whitespace
    and enforcing a maximum character length.

    Args:
        text: Raw user input.
        max_length: Maximum allowed character count. Defaults to 1000.

    Returns:
        Sanitized string, truncated to max_length if needed.
    """
    if not text:
        return ""
    return text.strip()[:max_length]
