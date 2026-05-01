"""
Unit Tests for the Conversation Service
Tests fallback logic, PII filtering, and message processing.
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import services.db as db_module
from services.db import MockDB
db_module.db = MockDB()

from services.conversation import fallback_logic, process_chat_message


class TestFallbackLogic(unittest.TestCase):
    """Tests for the fallback_logic function (used when Gemini API is unavailable)."""

    # --- English ---
    def test_fallback_english_register(self):
        """Should return registration info in English."""
        result = fallback_logic("how to register", "English")
        self.assertIn("Step 1", result)

    def test_fallback_english_timeline(self):
        """Should return timeline info in English."""
        result = fallback_logic("election timeline", "English")
        self.assertIn("timelines", result.lower())

    def test_fallback_english_roadmap(self):
        """Should return roadmap in English."""
        result = fallback_logic("Give me a roadmap", "English")
        self.assertIn("Roadmap", result)

    def test_fallback_english_process(self):
        """Should return process info in English."""
        result = fallback_logic("voting process steps", "English")
        self.assertIn("Step 1", result)

    def test_fallback_english_eligibility(self):
        """Should return eligibility info in English."""
        result = fallback_logic("eligibility to vote", "English")
        self.assertIn("18", result)

    def test_fallback_english_default(self):
        """Unknown query in English should return default message."""
        result = fallback_logic("hello there", "English")
        self.assertIn("Hi!", result)

    # --- Hindi ---
    def test_fallback_hindi_register(self):
        """Should return registration info in Hindi."""
        result = fallback_logic("register", "Hindi")
        self.assertIn("चरण", result)

    def test_fallback_hindi_default(self):
        """Unknown Hindi query should return Hindi default."""
        result = fallback_logic("hello", "Hindi")
        self.assertIn("नमस्ते", result)

    def test_fallback_hindi_roadmap(self):
        """Should return Hindi roadmap."""
        result = fallback_logic("my voting roadmap", "Hindi")
        self.assertIn("रोडमैप", result)

    # --- Kannada ---
    def test_fallback_kannada_default(self):
        """Unknown Kannada query should return Kannada default."""
        result = fallback_logic("hello", "Kannada")
        self.assertIn("ನಮಸ್ಕಾರ", result)

    def test_fallback_kannada_register(self):
        """Should return Kannada registration info."""
        result = fallback_logic("register to vote", "Kannada")
        self.assertIn("ಹಂತ", result)

    # --- Bengali ---
    def test_fallback_bengali_default(self):
        result = fallback_logic("hello", "Bengali")
        self.assertIn("নমস্কার", result)

    # --- Telugu ---
    def test_fallback_telugu_default(self):
        result = fallback_logic("hello", "Telugu")
        self.assertIn("నమస్కారం", result)

    # --- Marathi ---
    def test_fallback_marathi_default(self):
        result = fallback_logic("hello", "Marathi")
        self.assertIn("नमस्कार", result)

    # --- Tamil ---
    def test_fallback_tamil_default(self):
        result = fallback_logic("hello", "Tamil")
        self.assertIn("வணக்கம்", result)

    # --- Unknown Language ---
    def test_fallback_unknown_language_english_default(self):
        """Unknown language should fall back to English default."""
        result = fallback_logic("hello", "Swahili")
        self.assertIn("Hi!", result)

    def test_fallback_case_insensitivity_of_queries(self):
        """Fallback should handle mixed-case queries."""
        result = fallback_logic("REGISTER", "English")
        # lowercase is applied in function, so this should work
        self.assertIn("Step 1", result)


class TestProcessChatMessage(unittest.TestCase):
    """Tests for process_chat_message (without Gemini API)."""

    def setUp(self):
        """Use a fresh MockDB for each test."""
        db_module.db = MockDB()

    @patch('services.conversation.client', None)
    def test_process_valid_message_returns_string(self):
        """Should return a string response."""
        response, is_warning = process_chat_message("s1", "How do I register?", "India", "English")
        self.assertIsInstance(response, str)
        self.assertFalse(is_warning)

    @patch('services.conversation.client', None)
    def test_process_pii_returns_warning(self):
        """Should return is_warning=True when PII is detected."""
        response, is_warning = process_chat_message("s2", "My SSN is 123-45-6789", "USA", "English")
        self.assertTrue(is_warning)
        self.assertIn("WARNING", response)

    @patch('services.conversation.client', None)
    def test_process_aadhaar_pii_returns_warning(self):
        """Should catch Aadhaar as PII."""
        response, is_warning = process_chat_message("s3", "My Aadhaar is 1234 5678", "India", "English")
        self.assertTrue(is_warning)

    @patch('services.conversation.client', None)
    def test_process_saves_to_db(self):
        """Message should be saved to the DB after processing."""
        session_id = "db_test_session_999"
        process_chat_message(session_id, "timeline", "India", "English")
        messages = db_module.db.sessions.get(session_id, [])
        self.assertEqual(len(messages), 1)

    @patch('services.conversation.client', None)
    def test_process_hindi_response(self):
        """Should respond in Hindi fallback for Hindi language."""
        response, is_warning = process_chat_message("s_hi", "register", "India", "Hindi")
        self.assertFalse(is_warning)
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)

    @patch('services.conversation.client', None)
    def test_process_message_not_pii_does_not_warn(self):
        """A non-PII query should not return a warning."""
        response, is_warning = process_chat_message("s_safe", "What is the voting process?", "India", "English")
        self.assertFalse(is_warning)

    @patch('services.conversation.client', None)
    def test_process_returns_tuple(self):
        """process_chat_message should always return a 2-tuple."""
        result = process_chat_message("s_tuple", "hello", "General", "English")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    @patch('services.conversation.client', None)
    def test_process_roadmap_query(self):
        """Roadmap query should return a non-empty roadmap response."""
        response, is_warning = process_chat_message("s_road", "Give me a roadmap", "India", "English")
        self.assertFalse(is_warning)
        self.assertGreater(len(response), 10)

    @patch('services.conversation.client', None)
    def test_process_eligibility_query(self):
        """Eligibility query should include 18 in response."""
        response, is_warning = process_chat_message("s_elig", "Am I eligible to vote?", "India", "English")
        self.assertFalse(is_warning)
        self.assertIn("18", response)

    @patch('services.conversation.client', None)
    def test_process_multiple_messages_same_session(self):
        """Multiple messages to same session should all be stored."""
        sid = "multi_msg_session"
        process_chat_message(sid, "How do I register?", "India", "English")
        process_chat_message(sid, "What is the timeline?", "India", "English")
        messages = db_module.db.sessions.get(sid, [])
        self.assertEqual(len(messages), 2)


if __name__ == '__main__':
    unittest.main()
