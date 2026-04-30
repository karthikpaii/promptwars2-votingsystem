def scan_for_pii(text):
    """
    Scans the input text for Sensitive Personal Information (PII).
    Returns (True, message) if PII is found, (False, None) otherwise.
    """
    query = text.lower()
    if "ssn" in query or "aadhaar" in query or "password" in query:
        return True, "WARNING: Please do not share sensitive personal information like your SSN, Aadhaar, or passwords. I am a secure assistant and do not need this data to help you."
    return False, None
