import os
import logging
import json
import re
from typing import Tuple, List, Dict, Any, Optional
from google import genai
from services.security import scan_for_pii
from services.db import save_chat_message, get_chat_history

logger = logging.getLogger(__name__)
client: Optional[genai.Client] = None

# --- Configuration & Assets ---
SYSTEM_PROMPT = """You are a secure, intelligent Election Assistant. Guide users step-by-step.
Give ONE phase at a time. After each phase ask: "Do you want to continue to the next phase?"
Phases: 1-Registration, 2-Preparation, 3-Casting Vote, 4-Results.
For "Check Eligibility": ask ONE question at a time: citizen? 18+? registered?
For "My Voting Roadmap": give a personalised checklist.
NEVER ask for SSN, Aadhaar, passwords.
Always respond in the user's selected language.
After every response end with a clear question so the user knows what to do next."""

# Load translations from JSON
TRANSLATIONS_PATH = os.path.join(os.path.dirname(__file__), "translations.json")
try:
    with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
        TRANSLATIONS = json.load(f)
except Exception as e:
    logger.error("Failed to load translations: %s", e)
    TRANSLATIONS = {}

# Compiled regex for efficiency
_PHASE_REGEX = re.compile(r"phase (\d)|चरण (\d)|ಹಂತ (\d)|ধাপ (\d)|దశ (\d)|टप्पा (\d)|கட்டம் (\d)", re.IGNORECASE)
_YES_WORDS = [
    "yes",
    "continue",
    "next",
    "sure",
    "ok",
    "okay",
    "proceed",
    "go ahead",
    "✅",
    "yep",
    "yeah",
    "next step",
    "हां",
    "ಹೌದು",
    "হ্যাঁ",
    "అవును",
    "हो",
    "ஆம்",
]


def _detect_yes(query: str) -> bool:
    """Check if the user input implies agreement or desire to continue."""
    q = query.lower().strip()
    return any(w in q for w in _YES_WORDS)


def _get_current_phase(history: List[Dict[str, Any]]) -> int:
    """
    Detect the last discussed phase from the assistant's previous message.
    Looks for phase markers in multiple supported languages.
    """
    if not history:
        return 0
    last = history[-1].get("assistant_message", "")
    # Check for phase headers in various languages
    markers = ["Phase", "चरण", "ಹಂತ", "ধাপ", "దశ", "टप्पा", "கட்டம்"]
    for i in range(4, 0, -1):
        for marker in markers:
            if f"{marker} {i}" in last:
                return i
    return 0


def _get_eligibility_step(history: List[Dict[str, Any]]) -> int:
    """Returns which eligibility question to ask next (0-indexed)."""
    count = 0
    markers = [
        "Eligibility Check",
        "पात्रता जांच",
        "ಅರ್ಹತೆ ಪರೀಕ್ಷೆ",
        "যোগ্যতা যাচাই",
        "అర్హత తనిఖీ",
        "पात्रता तपासणी",
        "தகுதிச் சரிபார்ப்பு",
    ]
    for msg in history:
        a = msg.get("assistant_message", "")
        if any(m in a for m in markers):
            count += 1
    return count


def _actions_for_phase(phase: int) -> List[str]:
    """Returns contextual suggested actions based on the current phase."""
    if phase == 1:
        return ["✅ Yes, continue to Phase 2", "🗺️ My Voting Roadmap", "🔄 Start Over"]
    if phase == 2:
        return ["✅ Yes, continue to Phase 3", "⬅️ Back to Phase 1", "🔄 Start Over"]
    if phase == 3:
        return ["✅ Yes, continue to Phase 4", "⬅️ Back to Phase 2", "🔄 Start Over"]
    if phase == 4:
        return ["🗺️ My Voting Roadmap", "✅ Check Eligibility", "🏠 Start Over"]
    return [
        "📋 Register to Vote",
        "✅ Check Eligibility",
        "🗳️ Voting Process",
        "📅 Election Timelines",
        "🗺️ My Voting Roadmap",
    ]


def get_suggested_actions(response_text: str, is_warning: bool = False) -> List[str]:
    """
    Analyzes assistant response to determine the most relevant action buttons.
    Supports multilingual detection for phase headers and eligibility questions.
    """
    if is_warning:
        return ["🔄 Ask a different question", "🏠 Start Over"]

    r = response_text
    # Eligibility check detection
    if any(
        q in r
        for q in ["Question 1/3", "प्रश्न 1/3", "ಪ್ರಶ್ನೆ 1/3", "প্রশ্ন ১/৩", "ప్రశ్న 1/3", "प्रश्न १/३", "கேள்வி 1/3"]
    ):
        return ["✅ Yes", "❌ No"]
    if any(
        q in r
        for q in ["Question 2/3", "प्रश्न 2/3", "ಪ್ರಶ್ನೆ 2/3", "প্রশ্ন ২/৩", "ప్రశ్న 2/3", "प्रश्न २/३", "கேள்வி 2/3"]
    ):
        return ["✅ Yes", "❌ No"]
    if any(
        q in r
        for q in ["Question 3/3", "प्रश्न 3/3", "ಪ್ರಶ್ನೆ 3/3", "প্রশ্ন ৩/৩", "ప్రಶ್న 3/3", "प्रश्न ३/३", "கேள்வி 3/3"]
    ):
        return ["✅ Yes", "❌ No"]

    # Phase detection
    match = _PHASE_REGEX.search(r)
    if match:
        for group in match.groups():
            if group:
                return _actions_for_phase(int(group))

    if "roadmap" in r.lower() or "റോഡ്മാപ്പ്" in r:
        return ["📍 Find Polling Booth", "✅ Check Eligibility", "🏠 Start Over"]

    return _actions_for_phase(0)


def fallback_logic(
    query: str, language: str = "English", history: List[Dict[str, Any]] = None
) -> Tuple[str, List[str]]:
    """
    Hard-coded fallback logic for when Gemini API is unavailable.
    Provides rich, multilingual step-by-step guidance.
    """
    if history is None:
        history = []
    q = query.lower().strip()

    # Get language data, fallback to English if missing
    lang_data = TRANSLATIONS.get(language, TRANSLATIONS.get("English", {}))

    def get_phase_content(p: int) -> str:
        # Try language-specific phase, then English phase, then generic error
        phases = lang_data.get("phases", {})
        return phases.get(
            str(p), TRANSLATIONS.get("English", {}).get("phases", {}).get(str(p), "Phase content missing.")
        )

    # 1. Reset
    if "start over" in q:
        return lang_data.get("default", "Welcome!"), _actions_for_phase(0)

    # 2. Direct Phase Navigation
    match = _PHASE_REGEX.search(q)
    if match:
        for group in match.groups():
            if group:
                p = int(group)
                if 1 <= p <= 4:
                    return get_phase_content(p), _actions_for_phase(p)

    # 3. Continuation Logic
    if _detect_yes(q):
        current = _get_current_phase(history)
        nxt = current + 1
        if 1 <= nxt <= 4:
            return get_phase_content(nxt), _actions_for_phase(nxt)

    # 4. Content Intent Logic
    if any(k in q for k in ["eligible", "eligibility", "can i vote", "पात्रता", "ಅರ್ಹತೆ", "যোগ্যতা", "అర్హత"]):
        step = _get_eligibility_step(history)
        eligibility_list = lang_data.get("eligibility", TRANSLATIONS.get("English", {}).get("eligibility", []))
        if step < len(eligibility_list):
            return eligibility_list[step], ["✅ Yes", "❌ No"]

        # Simple evaluation
        answers = [m.get("user_message", "").lower() for m in history[-3:]]
        eligible = all(
            any(y in a for y in ["yes", "✅", "हां", "ಹೌದು", "হ্যাঁ", "అవును", "हो", "ஆம்"]) for a in answers
        )
        if eligible:
            return "🎉 **Eligible!** You're all set. Want your roadmap?", ["🗺️ Roadmap", "🏠 Start Over"]
        return "ℹ️ **Check Requirements.** You may need to register. Help with registration?", [
            "📋 Register",
            "🏠 Start Over",
        ]

    if any(
        k in q
        for k in ["roadmap", "road map", "റോഡ്മാപ്പ്", "रोडमॅप", "ರೋಡ್‌ಮ್ಯಾಪ್", "রোডম্যাপ", "రోడ్‌మ్యాప్", "வரைபடம்"]
    ):
        return lang_data.get("roadmap", TRANSLATIONS.get("English", {}).get("roadmap", "Roadmap missing.")), [
            "📍 Polling Booth",
            "🏠 Start Over",
        ]

    if any(k in q for k in ["register", "नोंदणी", "ನೋಂದಣಿ", "নিবন্ধন", "पंजीकरण", "నమోదు", "பதிவு"]):
        return get_phase_content(1), _actions_for_phase(1)

    if any(
        k in q for k in ["timeline", "date", "when", "समयरेखा", "ಸಮಯ", "সময়সীমা", "కాలక్రమం", "वेळापत्रक", "காலவரிசை"]
    ):
        return lang_data.get("timeline", TRANSLATIONS.get("English", {}).get("timeline", "Timeline missing.")), [
            "🗳️ Process",
            "🏠 Start Over",
        ]

    if any(
        k in q
        for k in [
            "process",
            "step",
            "how to vote",
            "voting process",
            "प्रक्रिया",
            "ಪ್ರಕ್ರಿಯೆ",
            "প্রক্রিয়া",
            "ప్రక్రియ",
        ]
    ):
        return get_phase_content(1), _actions_for_phase(1)

    # 5. Default Response
    return lang_data.get("default", "👋 Hi! How can I help?"), _actions_for_phase(0)


def process_chat_message(
    session_id: str, user_message: str, location: str = "General", language: str = "English"
) -> Tuple[str, bool, List[str]]:
    """
    Main entrypoint for chat processing. Coordinates PII scanning,
    Gemini API generation, and fallback logic.
    """
    # Security Scan
    has_pii, warning = scan_for_pii(user_message)
    if has_pii:
        return warning, True, ["🔄 Ask again", "🏠 Start Over"]

    global client
    if client is None:
        key = os.environ.get("GEMINI_API_KEY", "")
        if key:
            try:
                client = genai.Client(api_key=key)
            except Exception as e:
                logger.warning("Gemini Client Error: %s", e)

    history = get_chat_history(session_id)
    response_text = ""
    suggested_actions = []

    if client:
        try:
            h_ctx = "\n".join([f"User: {m['user_message']}\nAsst: {m['assistant_message']}" for m in history])
            prompt = (
                f"{SYSTEM_PROMPT}\nLocation: {location}\nLanguage: {language}\n"
                f"History:\n{h_ctx}\nRespond in {language}. End with a question.\nUser: {user_message}"
            )
            res = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
            response_text = res.text
            suggested_actions = get_suggested_actions(response_text)
        except Exception as e:
            logger.error("Gemini runtime error: %s", e)

    # Fallback if AI fails or key is missing
    if not response_text:
        response_text, suggested_actions = fallback_logic(user_message, language, history)
        if not client:
            response_text += "\n\n*(Local mode)*"

    save_chat_message(session_id, user_message, response_text)
    return response_text, False, suggested_actions
