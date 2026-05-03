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

    def test_fallback_english_register(self):
        """Should return registration info in English."""
        result, actions = fallback_logic("how to register", "English")
        self.assertIn("Phase 1", result)
        self.assertIn("✅ Yes", actions[0])

    def test_fallback_english_timeline(self):
        """Should return timeline info in English."""
        result, _ = fallback_logic("election timeline", "English")
        self.assertIn("Timeline", result)

    def test_fallback_english_roadmap(self):
        """Should return roadmap in English."""
        result, _ = fallback_logic("Give me a roadmap", "English")
        self.assertIn("Roadmap", result)

    def test_fallback_english_default(self):
        """Unknown query in English should return default message."""
        result, _ = fallback_logic("hello there", "English")
        self.assertIn("Hi!", result)

    def test_fallback_hindi_register(self):
        """Should return registration info in Hindi."""
        result, _ = fallback_logic("पंजीकरण", "Hindi")
        self.assertIn("चरण 1", result)

    def test_fallback_hindi_default(self):
        """Unknown Hindi query should return Hindi default."""
        result, _ = fallback_logic("hello", "Hindi")
        self.assertIn("नमस्ते", result)

    def test_fallback_unknown_language_english_default(self):
        """Unknown language should fall back to English default."""
        result, _ = fallback_logic("hello", "Swahili")
        self.assertIn("Hi!", result)

    def test_fallback_case_insensitivity(self):
        """Fallback should handle mixed-case queries."""
        result, _ = fallback_logic("REGISTER", "English")
        self.assertIn("Phase 1", result)


class TestProcessChatMessage(unittest.TestCase):
    """Tests for process_chat_message (without Gemini API)."""

    def setUp(self):
        """Use a fresh MockDB for each test."""
        db_module.db = MockDB()

    @patch('services.conversation.client', None)
    def test_process_valid_message_returns_3_tuple(self):
        """Should return (text, is_warning, actions)."""
        response, is_warning, actions = process_chat_message("s1", "How do I register?", "India", "English")
        self.assertIsInstance(response, str)
        self.assertFalse(is_warning)
        self.assertIsInstance(actions, list)

    @patch('services.conversation.client', None)
    def test_process_pii_returns_warning(self):
        """Should return is_warning=True when PII is detected."""
        response, is_warning, _ = process_chat_message("s2", "My SSN is 123-45-6789", "USA", "English")
        self.assertTrue(is_warning)
        self.assertIn("WARNING", response)

    @patch('services.conversation.client', None)
    def test_process_saves_to_db(self):
        """Message should be saved to the DB after processing."""
        session_id = "db_test_session_999"
        process_chat_message(session_id, "timeline", "India", "English")
        messages = db_module.db.get_messages(session_id)
        self.assertEqual(len(messages), 1)

    @patch('services.conversation.client', None)
    def test_process_hindi_response(self):
        """Should respond in Hindi fallback for Hindi language."""
        response, is_warning, _ = process_chat_message("s_hi", "पंजीकरण", "India", "Hindi")
        self.assertFalse(is_warning)
        self.assertIn("चरण 1", response)

    @patch('services.conversation.client', None)
    def test_process_multiple_messages_same_session(self):
        """Multiple messages to same session should all be stored."""
        sid = "multi_msg_session"
        process_chat_message(sid, "How do I register?", "India", "English")
        process_chat_message(sid, "What is the timeline?", "India", "English")
        messages = db_module.db.get_messages(sid)
        self.assertEqual(len(messages), 2)

    def test_response_caching(self):
        """Identical queries should return cached responses for efficiency."""
        from services.conversation import _RESPONSE_CACHE
        _RESPONSE_CACHE.clear()
        
        sid = "cache_test"
        msg = "Is voting important?"
        
        # First call (simulated)
        with patch('services.conversation.client') as mock_client:
            mock_client.models.generate_content.return_value.text = "Yes, very."
            res1, _, _ = process_chat_message(sid, msg, "USA", "English")
            self.assertEqual(res1, "Yes, very.")
            self.assertEqual(mock_client.models.generate_content.call_count, 1)
        
        # Second call (should be cached)
        with patch('services.conversation.client') as mock_client:
            res2, _, _ = process_chat_message(sid, msg, "USA", "English")
            self.assertEqual(res2, "Yes, very.")
            self.assertEqual(mock_client.models.generate_content.call_count, 0)


if __name__ == '__main__':
    unittest.main()
