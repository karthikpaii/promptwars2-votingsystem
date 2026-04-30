from flask import Flask, render_template, request, jsonify
import os
import uuid
from dotenv import load_dotenv

# Import our modular services
from services.conversation import process_chat_message
from services.db import init_db

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-election-assistant')

# Initialize DB (Firestore or MockDB) on app startup
init_db()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_query = data.get("message", "").strip()
    session_id = data.get("session_id", str(uuid.uuid4()))
    location = data.get("location", "General (No specific region)")
    language = data.get("language", "English")
    
    if not user_query:
        return jsonify({"status": "error", "message": "Empty query"}), 400

    # Delegate to the conversation service
    response_text, is_warning = process_chat_message(session_id, user_query, location, language)
    
    if is_warning:
        # We can prepend a flag or handle it gracefully on the client
        response_text = f"WARNING: {response_text}" if not response_text.startswith("WARNING") else response_text

    return jsonify({
        "status": "success",
        "message": response_text,
        "session_id": session_id
    })

@app.route("/api/subscribe", methods=["POST"])
def subscribe():
    data = request.json
    email = data.get("email")
    location = data.get("location")
    
    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400
        
    # In a real app, you would save this to Firestore here:
    # db.collection('subscribers').add({"email": email, "location": location})
    print(f"New Subscriber: {email} for region {location}")
    
    return jsonify({"status": "success", "message": "Subscribed successfully"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
