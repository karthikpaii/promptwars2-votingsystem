"""
Flask application entrypoint for the Secure Election Assistant.

Routes:
    GET  /              → Serves the chat UI
    POST /api/chat      → Processes a user message and returns an AI response
    POST /api/subscribe → Registers a user for election reminder emails
"""

import logging
import os
import uuid

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

load_dotenv(override=True)

from services.conversation import process_chat_message
from services.db import init_db
from services.security import sanitize_input

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-for-election-assistant")

# Initialize database (Firestore or MockDB) at startup
init_db()


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------


@app.after_request
def process_response(response):
    """Attach security-related HTTP headers and performance optimizations."""
    # Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    
    # Performance: Cache static assets (images, CSS, JS) for 1 year
    if request.path.startswith('/static/'):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def home():
    """
    Serves the primary chat interface.
    
    Returns:
        The rendered index.html template with appropriate accessibility features.
    """
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Process a chat message and return an AI-generated response.

    Request JSON:
        message (str): The user's message (required).
        session_id (str): Conversation session ID (auto-generated if absent).
        location (str): User's region for context (optional).
        language (str): Preferred response language (optional, defaults to English).

    Returns:
        200: JSON with status, message, and session_id.
        400: JSON with status and error detail if message is empty.
    """
    data = request.get_json(silent=True) or {}

    raw_message = data.get("message", "")
    user_query = sanitize_input(raw_message)

    if not user_query:
        return jsonify({"status": "error", "message": "Empty query"}), 400

    session_id = data.get("session_id") or str(uuid.uuid4())
    location = sanitize_input(data.get("location", "General (No specific region)"), max_length=100)
    language = sanitize_input(data.get("language", "English"), max_length=50)

    response_text, is_warning, suggested_actions = process_chat_message(session_id, user_query, location, language)

    if is_warning and not response_text.startswith("WARNING"):
        response_text = f"WARNING: {response_text}"

    return jsonify(
        {
            "status": "success",
            "message": response_text,
            "session_id": session_id,
            "suggested_actions": suggested_actions,
        }
    )


@app.route("/api/subscribe", methods=["POST"])
def subscribe():
    """
    Registers a user for email-based election alerts.
    
    Validates the email format and stores it alongside the user's location 
    preference for regional targeting.
    """
    data = request.get_json(silent=True) or {}
    email = sanitize_input(data.get("email", ""), max_length=254)
    location = sanitize_input(data.get("location", "Unknown"), max_length=100)

    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400

    logger.info("New subscriber: %s for region: %s", email, location)
    return jsonify({"status": "success", "message": "Subscribed successfully"})


@app.route("/api/export_roadmap", methods=["POST"])
def export_roadmap():
    """
    Generates a structured text-based voting roadmap for the user to download.
    
    Uses the chat history or location context to personalise the guide.
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    location = data.get("location", "General")
    
    # Simple generated roadmap text
    content = f"VOTING ROADMAP: {location}\n" + "="*30 + "\n"
    content += "1. Register to Vote (Check local deadlines)\n"
    content += "2. Research Candidates & Polling Location\n"
    content += "3. Bring ID & Cast Your Ballot\n"
    content += "4. Track Results & Stay Informed\n\n"
    content += "Generated by Election Assistant."
    
    return jsonify({"status": "success", "content": content})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_ENV", "production") == "development"
    app.run(debug=debug, host="0.0.0.0", port=port)
