"""
Unit Tests for the Security Service (PII Scanning)
Tests all edge cases for the scan_for_pii function.
"""
import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.security import scan_for_pii


class TestScanForPII(unittest.TestCase):
    """Tests for the PII scanning functionality."""

    # --- Positive Cases (PII Detected) ---

    def test_detects_ssn_keyword(self):
        """Should flag messages containing 'ssn'."""
        found, message = scan_for_pii("My SSN is 123-45-6789")
        self.assertTrue(found)
        self.assertIn("WARNING", message)

    def test_detects_aadhaar_keyword(self):
        """Should flag messages containing 'aadhaar'."""
        found, message = scan_for_pii("My Aadhaar number is 1234 5678 9012")
        self.assertTrue(found)
        self.assertIn("WARNING", message)

    def test_detects_password_keyword(self):
        """Should flag messages containing 'password'."""
        found, message = scan_for_pii("My password is hunter2")
        self.assertTrue(found)
        self.assertIn("WARNING", message)

    def test_case_insensitive_ssn(self):
        """PII detection should be case-insensitive for SSN."""
        found, message = scan_for_pii("What is SSN used for?")
        self.assertTrue(found)

    def test_case_insensitive_aadhaar(self):
        """PII detection should be case-insensitive for Aadhaar."""
        found, message = scan_for_pii("AADHAAR CARD")
        self.assertTrue(found)

    def test_case_insensitive_password(self):
        """PII detection should be case-insensitive for password."""
        found, message = scan_for_pii("PASSWORD RESET")
        self.assertTrue(found)

    # --- Negative Cases (No PII) ---

    def test_safe_election_query(self):
        """Should not flag a normal election-related query."""
        found, message = scan_for_pii("How do I register to vote?")
        self.assertFalse(found)
        self.assertIsNone(message)

    def test_empty_string(self):
        """Should not flag an empty string."""
        found, message = scan_for_pii("")
        self.assertFalse(found)
        self.assertIsNone(message)

    def test_safe_timeline_query(self):
        """Should not flag a question about election timelines."""
        found, message = scan_for_pii("When is the next election in California?")
        self.assertFalse(found)
        self.assertIsNone(message)

    def test_safe_eligibility_query(self):
        """Should not flag an eligibility question."""
        found, message = scan_for_pii("Am I eligible to vote at 18?")
        self.assertFalse(found)
        self.assertIsNone(message)

    def test_safe_roadmap_query(self):
        """Should not flag a request for a voting roadmap."""
        found, message = scan_for_pii("Give me my voting roadmap for India.")
        self.assertFalse(found)
        self.assertIsNone(message)

    def test_returns_tuple(self):
        """scan_for_pii should always return a 2-tuple."""
        result = scan_for_pii("test")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_pii_warning_message_is_string(self):
        """Warning message returned when PII is found should be a string."""
        found, message = scan_for_pii("ssn")
        self.assertTrue(found)
        self.assertIsInstance(message, str)

    def test_no_pii_second_element_is_none(self):
        """Second element of tuple should be None when no PII found."""
        found, message = scan_for_pii("How do I vote?")
        self.assertIsNone(message)

    def test_pii_in_multilingual_text(self):
        """Should detect English PII keywords even in mixed-language text."""
        found, _ = scan_for_pii("मेरा password kya hai?")
        self.assertTrue(found)

    def test_whitespace_only(self):
        """Should not flag whitespace-only input."""
        found, message = scan_for_pii("   ")
        self.assertFalse(found)
        self.assertIsNone(message)


if __name__ == '__main__':
    unittest.main()
