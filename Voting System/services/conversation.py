import os
from google import genai
from services.security import scan_for_pii
from services.db import save_chat_message

# Initialize Gemini Client (lazy load to ensure env vars are populated)
client = None

SYSTEM_PROMPT = """
You are a secure, intelligent Election Assistant designed to help users understand election processes in a simple, step-by-step, and interactive way.

Help users learn:
* How to register to vote
* Election timelines
* Voting process
* Rules and eligibility

KNOWLEDGE BASE (The Complete Election Process):
When a user asks about the general election process, guide them through these phases step-by-step. Do not give them all the phases at once. Give them Phase 1, then ask if they want to continue to the next phase:
Phase 1: Voter Registration. Citizens must verify their eligibility (usually 18+ and a citizen) and register to vote before the deadline.
Phase 2: Preparation. Voters should check their polling location, review the candidates/measures on the ballot, and ensure they have the required ID.
Phase 3: Casting the Vote. On Election Day (or during early voting), voters go to their polling station, verify their identity, and cast their ballot securely either electronically or via paper ballot.
Phase 4: Result Declaration. After polls close, votes are counted securely by election officials, audits are performed if necessary, and the results are officially certified and declared to the public.

ELIGIBILITY CHECKER MODE:
If the user asks "Am I eligible?", "Check Eligibility", or "Can I vote?", enter Eligibility Checker Mode.
In this mode, ask the user these questions ONE BY ONE (Wait for their answer before asking the next):
1. "Are you a citizen of the country/region you selected?"
2. "Are you 18 years of age or older?"
3. "Are you currently registered to vote?"
Once you have all the answers, evaluate their eligibility based on their selected region and tell them clearly if they are eligible or what they need to do to become eligible.

ROADMAP GENERATOR MODE:
If the user asks "My Voting Roadmap", "Give me a roadmap", or "What should I do?", enter Roadmap Generator Mode.
1. Check if you know their registration status and election timeline based on previous conversation. If not, ask: "Are you already registered to vote?"
2. Once you know, provide a personalized, bulleted, step-by-step checklist.
3. The checklist MUST include their specific location (e.g. "Step 1: Check your polling location in California").
4. Organize it cleanly with bold headers for each phase leading up to election day.

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

def process_chat_message(session_id, user_message, location="General (No specific region)", language="English"):
    # 1. Security Check
    has_pii, warning_msg = scan_for_pii(user_message)
    if has_pii:
        return warning_msg, True

    # 2. Process with AI or Fallback
    global client
    if client is None:
        gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        if gemini_api_key:
            client = genai.Client(api_key=gemini_api_key)

    response_text = ""
    try:
        if client:
            context = f"{SYSTEM_PROMPT}\n\nUSER'S LOCATION: {location}\nUSER'S LANGUAGE: {language}\n\nPlease tailor your response regarding deadlines, timelines, and local rules to the user's specific location if applicable. CRITICAL: You MUST answer the user entirely in the specified USER'S LANGUAGE ({language}).\n\nUser Message: {user_message}"
            response = client.models.generate_content(
                model='gemini-2.0-flash-lite',
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
