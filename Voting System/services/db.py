import os
import time

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    firebase_admin = None

db = None

def init_db():
    global db
    if firebase_admin and not firebase_admin._apps:
        cred_path = os.environ.get("FIREBASE_CREDENTIALS")
        if cred_path and os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                db = firestore.client()
                print("Firestore initialized.")
            except Exception as e:
                print(f"Firestore initialization failed: {e}. Using MockDB.")
                db = MockDB()
        else:
            print("No Firebase credentials found. Running with local mock DB.")
            db = MockDB()
    elif not firebase_admin:
        print("Firebase Admin SDK not installed. Running with local mock DB.")
        db = MockDB()

class MockDB:
    def __init__(self):
        self.sessions = {}
        
    def save_message(self, session_id, message_data):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(message_data)

def save_chat_message(session_id, user_message, assistant_message):
    if db is None:
        init_db()
        
    message_data = {
        "user_message": user_message,
        "assistant_message": assistant_message,
        "timestamp": time.time()
    }
    
    if isinstance(db, MockDB):
        db.save_message(session_id, message_data)
    else:
        try:
            # Actual Firestore write
            doc_ref = db.collection('sessions').document(session_id)
            doc_ref.set({"lastActive": time.time()}, merge=True)
            doc_ref.collection('messages').add(message_data)
        except Exception as e:
            print(f"Error writing to Firestore: {e}")
