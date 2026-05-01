"""
Integration Tests for Flask API Endpoints
Tests all routes: /, /api/chat, /api/subscribe
"""
import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Patch init_db so it doesn't try to connect to Firebase on import
with patch('services.db.init_db', return_value=None):
    import services.db as db_module
    from services.db import MockDB
    db_module.db = MockDB()

import app as flask_app_module
flask_app_module.app.config['TESTING'] = True
flask_app_module.app.config['SECRET_KEY'] = 'test-secret-key'


class TestHomeRoute(unittest.TestCase):
    """Tests for the / route."""

    def setUp(self):
        self.client = flask_app_module.app.test_client()

    def test_home_returns_200(self):
        """GET / should return HTTP 200 OK."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_home_returns_html(self):
        """GET / should return HTML content."""
        response = self.client.get('/')
        self.assertIn(b'html', response.data.lower())


class TestChatRoute(unittest.TestCase):
    """Tests for the /api/chat route."""

    def setUp(self):
        self.client = flask_app_module.app.test_client()
        db_module.db = MockDB()

    def _post_chat(self, payload):
        return self.client.post(
            '/api/chat',
            data=json.dumps(payload),
            content_type='application/json'
        )

    @patch('services.conversation.client', None)
    def test_chat_empty_message_returns_400(self):
        """POST /api/chat with empty message should return 400."""
        response = self._post_chat({"message": "", "session_id": "s1"})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')

    @patch('services.conversation.client', None)
    def test_chat_valid_message_returns_200(self):
        """POST /api/chat with valid message should return 200."""
        response = self._post_chat({
            "message": "How do I register to vote?",
            "session_id": "test_session_001",
            "location": "India",
            "language": "English"
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('message', data)
        self.assertIn('suggested_actions', data)

    @patch('services.conversation.client', None)
    def test_chat_pii_detected_returns_warning(self):
        """POST /api/chat with PII should return a WARNING in the message."""
        response = self._post_chat({
            "message": "My SSN is 123-45-6789",
            "session_id": "pii_session",
            "location": "USA"
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('WARNING', data['message'])

    @patch('services.conversation.client', None)
    def test_chat_auto_generates_session_id(self):
        """POST /api/chat without session_id should auto-generate one."""
        response = self._post_chat({
            "message": "What is the voting process?"
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('session_id', data)


class TestSubscribeRoute(unittest.TestCase):
    """Tests for the /api/subscribe route."""

    def setUp(self):
        self.client = flask_app_module.app.test_client()

    def _post_subscribe(self, payload):
        return self.client.post(
            '/api/subscribe',
            data=json.dumps(payload),
            content_type='application/json'
        )

    def test_subscribe_valid_email_returns_200(self):
        """POST /api/subscribe with valid email should return 200."""
        response = self._post_subscribe({"email": "test@example.com"})
        self.assertEqual(response.status_code, 200)

    def test_subscribe_missing_email_returns_400(self):
        """POST /api/subscribe without email should return 400."""
        response = self._post_subscribe({"location": "India"})
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
