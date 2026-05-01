"""
Unit Tests for the Database Service (MockDB)
Tests all core data storage and retrieval operations.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.db import MockDB, save_chat_message, get_chat_history, init_db
import services.db as db_module


class TestMockDB(unittest.TestCase):
    """Tests for the MockDB in-memory store."""

    def setUp(self):
        """Initialize a fresh MockDB for each test."""
        self.db = MockDB()

    def test_save_message_creates_session(self):
        """Saving a message should create a new session entry."""
        self.db.save_message("session_1", {"user_message": "Hello", "assistant_message": "Hi!"})
        self.assertIn("session_1", self.db.sessions)

    def test_save_message_appends(self):
        """Multiple messages should be appended to the same session."""
        self.db.save_message("session_A", {"user_message": "Hello", "assistant_message": "Hi!"})
        self.db.save_message("session_A", {"user_message": "How do I vote?", "assistant_message": "Step 1..."})
        self.assertEqual(len(self.db.sessions["session_A"]), 2)

    def test_save_message_stores_correct_data(self):
        """Saved message should contain correct user and assistant messages."""
        msg = {"user_message": "Test query", "assistant_message": "Test response"}
        self.db.save_message("s1", msg)
        stored = self.db.sessions["s1"][0]
        self.assertEqual(stored["user_message"], "Test query")
        self.assertEqual(stored["assistant_message"], "Test response")

    def test_multiple_sessions_isolated(self):
        """Messages from different sessions should not interfere."""
        self.db.save_message("s1", {"user_message": "Hi", "assistant_message": "Hello"})
        self.db.save_message("s2", {"user_message": "Register", "assistant_message": "Step 1..."})
        self.assertEqual(len(self.db.sessions["s1"]), 1)
        self.assertEqual(len(self.db.sessions["s2"]), 1)

    def test_empty_sessions_on_init(self):
        """New MockDB should start with no sessions."""
        fresh_db = MockDB()
        self.assertEqual(len(fresh_db.sessions), 0)

    def test_session_not_found_returns_empty(self):
        """Accessing a nonexistent session should return an empty list."""
        result = self.db.sessions.get("nonexistent", [])
        self.assertEqual(result, [])


class TestSaveChatMessage(unittest.TestCase):
    """Integration tests for save_chat_message using MockDB."""

    def setUp(self):
        """Ensure db_module uses a fresh MockDB before each test."""
        db_module.db = MockDB()

    def test_save_chat_message_stores_data(self):
        """save_chat_message should persist messages in the mock db."""
        save_chat_message("test_session", "user msg", "ai response")
        stored = db_module.db.sessions.get("test_session", [])
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["user_message"], "user msg")
        self.assertEqual(stored[0]["assistant_message"], "ai response")

    def test_save_chat_message_includes_timestamp(self):
        """Saved messages should include a timestamp."""
        save_chat_message("ts_session", "hi", "hello")
        stored = db_module.db.sessions["ts_session"][0]
        self.assertIn("timestamp", stored)
        self.assertIsInstance(stored["timestamp"], float)

    def test_save_multiple_messages_same_session(self):
        """Multiple messages to same session should accumulate."""
        save_chat_message("session_x", "msg1", "resp1")
        save_chat_message("session_x", "msg2", "resp2")
        self.assertEqual(len(db_module.db.sessions["session_x"]), 2)


class TestGetChatHistory(unittest.TestCase):
    """Tests for get_chat_history with MockDB."""

    def setUp(self):
        """Populate MockDB with sample data."""
        db_module.db = MockDB()
        for i in range(10):
            save_chat_message("history_session", f"user_{i}", f"bot_{i}")

    def test_get_chat_history_returns_list(self):
        """Should return a list."""
        result = get_chat_history("history_session")
        self.assertIsInstance(result, list)

    def test_get_chat_history_default_limit_5(self):
        """Default limit should return at most 5 messages."""
        result = get_chat_history("history_session")
        self.assertLessEqual(len(result), 5)

    def test_get_chat_history_custom_limit(self):
        """Custom limit should be respected."""
        result = get_chat_history("history_session", limit=3)
        self.assertEqual(len(result), 3)

    def test_get_chat_history_empty_session(self):
        """Non-existent session should return empty list."""
        result = get_chat_history("does_not_exist")
        self.assertEqual(result, [])

    def test_get_chat_history_returns_recent_messages(self):
        """Should return the most recent messages (last N)."""
        result = get_chat_history("history_session", limit=5)
        # Last 5 messages should have user_5 through user_9
        user_messages = [m["user_message"] for m in result]
        self.assertIn("user_9", user_messages)


class TestInitDb(unittest.TestCase):
    """Tests for the init_db function."""

    def test_init_db_creates_mock_db_when_no_firebase(self):
        """init_db should create a MockDB when Firebase is not configured."""
        db_module.db = None
        init_db()
        self.assertIsNotNone(db_module.db)
        self.assertIsInstance(db_module.db, MockDB)


if __name__ == '__main__':
    unittest.main()
