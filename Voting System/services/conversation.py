import os
from google import genai
from services.security import scan_for_pii
from services.db import save_chat_message

# Initialize Gemini Client
gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
client = None
if gemini_api_key:
    client = genai.Client(api_key=gemini_api_key)

SYSTEM_PROMPT = """
You are a secure, intelligent Election Assistant designed to help users understand election processes in a simple, step-by-step, and interactive way.

Help users learn:
* How to register to vote
* Election timelines
* Voting process
* Rules and eligibility

CRITICAL RULES:
* Never ask for sensitive personal data (Aadhaar, SSN, passwords).
* Do not store personal user information.
* Only provide verified, neutral, and non-political information.
* Clearly warn users if they attempt to share sensitive data.

BEHAVIOR:
* Adapt answers based on the user's country/region. If you don't know it, ask them.
* Provide step-by-step guidance.
* Ask follow-up questions to guide users.
* Keep responses simple and structured.

STYLE:
* Beginner-friendly.
* Use numbered steps.
* Use short explanations.
* After explaining a step, always ask: "Do you want to continue?"
"""

def fallback_logic(query):
    query = query.lower()
    if "register" in query:
        return "Step 1: Check your eligibility to vote based on your region.\nDo you want to continue?"
    if "timeline" in query or "date" in query or "when" in query:
        return "Election timelines vary by country. Please tell me your country or state so I can give you the exact dates.\nDo you want to continue?"
    if "process" in query or "step" in query or "how to vote" in query:
        return "Step 1: Before voting day, verify your polling station location online.\nDo you want to continue?"
    if "rule" in query or "eligibility" in query or "eligible" in query:
        return "Step 1: In most places, you must be at least 18 years old and a citizen to vote.\nDo you want to continue?"
    return "Hi! I can guide you through the election process. What would you like to learn?"

def process_chat_message(session_id, user_message):
    # 1. Security Check
    has_pii, warning_msg = scan_for_pii(user_message)
    if has_pii:
        return warning_msg, True

    # 2. Process with AI or Fallback
    response_text = ""
    try:
        if client:
            context = f"{SYSTEM_PROMPT}\n\nUser Message: {user_message}"
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=context
            )
            response_text = response.text
        else:
            response_text = fallback_logic(user_message) + "\n\n*(Using local logic - set GEMINI_API_KEY for full AI power)*"
    except Exception as e:
        print(f"Gemini Error: {e}")
        response_text = fallback_logic(user_message)

    # 3. Database Write (Telemetry/Context)
    save_chat_message(session_id, user_message, response_text)

    return response_text, False
