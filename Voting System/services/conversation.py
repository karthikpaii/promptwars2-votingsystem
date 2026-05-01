import os
import logging
from typing import Tuple, List
from google import genai
from services.security import scan_for_pii
from services.db import save_chat_message, get_chat_history

logger = logging.getLogger(__name__)
client = None

SYSTEM_PROMPT = """You are a secure, intelligent Election Assistant. Guide users step-by-step.
Give ONE phase at a time. After each phase ask: "Do you want to continue to the next phase?"
Phases: 1-Registration, 2-Preparation, 3-Casting Vote, 4-Results.
For "Check Eligibility": ask ONE question at a time: citizen? 18+? registered?
For "My Voting Roadmap": give a personalised checklist.
NEVER ask for SSN, Aadhaar, passwords.
Always respond in the user's selected language.
After every response end with a clear question so the user knows what to do next."""

PHASE_CONTENT = {
    1: """🗳️ **Phase 1: Voter Registration**

Here's what you need to do first:

**Step 1 — Check Eligibility:**
• Are you 18 years or older?
• Are you a citizen of the country?

**Step 2 — Gather Documents:**
• Government-issued Photo ID (Passport, Voter ID, Driver's License)
• Proof of address (Utility bill, Bank statement)

**Step 3 — Register:**
• Visit your local election office OR register online at your government's election portal
• Fill the registration form carefully

**Step 4 — Confirm Registration:**
• You'll receive a confirmation card/email — keep it safe!
• Double-check your registration before the deadline

⏰ Deadlines vary by region — check your local election authority website.

Ready to move on? **Do you want to continue to Phase 2: Preparation?**""",

    2: """📋 **Phase 2: Preparation**

Great! Now let's prepare for Election Day:

**Step 1 — Find Your Polling Location:**
• Check your registration letter or the official election website
• Note the address and opening/closing hours

**Step 2 — Review the Ballot:**
• Research the candidates in your area
• Understand the issues and measures you'll be voting on

**Step 3 — Prepare Your Documents:**
• Check what ID is required at your polling station
• Some regions allow digital ID, others require physical documents

**Step 4 — Plan Your Trip:**
• Arrange transport to your polling station
• Note: early voting may be available in your region!

**Do you want to continue to Phase 3: Casting Your Vote?**""",

    3: """🏛️ **Phase 3: Casting Your Vote**

It's Election Day! Here's what to do:

**Step 1 — Arrive at Your Polling Station:**
• Bring your required ID and confirmation documents
• Go early to avoid long queues

**Step 2 — Check In:**
• Election officials will verify your identity
• Your name will be marked off the voter roll

**Step 3 — Receive Your Ballot:**
• You'll get a ballot paper or be guided to a voting machine
• Read all instructions carefully

**Step 4 — Cast Your Vote:**
• Mark your ballot clearly as instructed
• For paper: fold and place in the ballot box
• For electronic: confirm your selection before submitting

**Step 5 — You're Done! 🎉**
• Some stations give an "I Voted" sticker!

**Do you want to continue to Phase 4: Result Declaration?**""",

    4: """📊 **Phase 4: Result Declaration**

Here's what happens after you vote:

**Step 1 — Polls Close:**
• When the polling period ends, voting stops
• The official counting begins

**Step 2 — Vote Counting:**
• Officials count all ballots (paper + electronic)
• Independent observers verify for fairness

**Step 3 — Audits (if needed):**
• Close results may trigger a recount or audit
• This ensures accuracy and fairness

**Step 4 — Results Announced:**
• Preliminary results announced (may take hours/days)
• Winners are officially certified by election authorities

**Step 5 — Certification:**
• Results published and elected officials take office

🎉 **You've completed the full election process guide!**
What would you like to do next?""",
}

ELIGIBILITY_QUESTIONS = [
    "**Eligibility Check — Question 1/3:**\n\nAre you a **citizen** of the country/region you selected?",
    "**Eligibility Check — Question 2/3:**\n\nAre you **18 years of age or older?**",
    "**Eligibility Check — Question 3/3:**\n\nAre you currently **registered to vote?**",
]


def _detect_yes(query: str) -> bool:
    yes_words = ["yes", "continue", "next", "sure", "ok", "okay", "proceed", "go ahead", "✅", "yep", "yeah", "next step"]
    q = query.lower().strip()
    return any(w in q for w in yes_words)


def _get_current_phase(history: list) -> int:
    """Detect phase from the START of the last assistant message (not mentions within it)."""
    if not history:
        return 0
    last = history[-1].get("assistant_message", "")
    # Use startswith on the emoji+heading that uniquely opens each phase block
    if last.startswith("📊 **Phase 4"):
        return 4
    if last.startswith("🏛️ **Phase 3"):
        return 3
    if last.startswith("📋 **Phase 2"):
        return 2
    if last.startswith("🗳️ **Phase 1"):
        return 1
    return 0


def _get_eligibility_step(history: list) -> int:
    """Returns which eligibility question to ask next (0-indexed)."""
    count = 0
    for msg in history:
        a = msg.get("assistant_message", "").lower()
        if "eligibility check" in a:
            count += 1
    return count


def _actions_for_phase(phase: int) -> List[str]:
    if phase == 1:
        return ["✅ Yes, continue to Phase 2", "🗺️ My Voting Roadmap", "🔄 Start Over"]
    if phase == 2:
        return ["✅ Yes, continue to Phase 3", "⬅️ Back to Phase 1", "🔄 Start Over"]
    if phase == 3:
        return ["✅ Yes, continue to Phase 4", "⬅️ Back to Phase 2", "🔄 Start Over"]
    if phase == 4:
        return ["🗺️ My Voting Roadmap", "✅ Check Eligibility", "🏠 Start Over"]
    return ["📋 Register to Vote", "✅ Check Eligibility", "🗳️ Voting Process", "📅 Election Timelines", "🗺️ My Voting Roadmap"]


def get_suggested_actions(response_text: str, is_warning: bool = False) -> List[str]:
    if is_warning:
        return ["🔄 Ask a different question", "🏠 Start Over"]
    r = response_text.lower()
    if "question 1/3" in r:
        return ["✅ Yes, I am a citizen", "❌ No, I'm not a citizen"]
    if "question 2/3" in r:
        return ["✅ Yes, I'm 18+", "❌ No, I'm under 18"]
    if "question 3/3" in r:
        return ["✅ Yes, I'm registered", "❌ No, not yet registered"]
    if "phase 4" in r or "result declaration" in r:
        return _actions_for_phase(4)
    if "phase 3" in r or "casting your vote" in r:
        return _actions_for_phase(3)
    if "phase 2" in r or "preparation" in r:
        return _actions_for_phase(2)
    if "phase 1" in r or "voter registration" in r:
        return _actions_for_phase(1)
    if "roadmap" in r or "checklist" in r:
        return ["📍 Find My Polling Booth", "✅ Check Eligibility", "🏠 Start Over"]
    if "do you want to continue" in r or "would you like" in r:
        return ["✅ Yes, continue!", "🔄 Start Over"]
    if "eligible" in r and ("congratulations" in r or "not eligible" in r):
        return ["🗺️ My Voting Roadmap", "📋 Register to Vote", "🏠 Start Over"]
    return ["📋 Register to Vote", "✅ Check Eligibility", "🗳️ Voting Process", "📅 Election Timelines", "🗺️ My Voting Roadmap"]


TRANSLATIONS = {
    "Hindi": {
        "default": "नमस्ते! मैं चुनाव प्रक्रिया में आपका मार्गदर्शन कर सकता हूँ। आप क्या जानना चाहेंगे?",
        "register": "**चरण 1: मतदाता पंजीकरण**\nपहले अपनी पात्रता जांचें (18+ और नागरिक)। फिर अपने दस्तावेज़ एकत्र करें और स्थानीय चुनाव कार्यालय में पंजीकरण करें।\nक्या आप जारी रखना चाहते हैं?",
        "roadmap": "**आपका व्यक्तिगत रोडमैप:**\n1. यदि पंजीकृत नहीं → 10 अक्टूबर से पहले पंजीकरण करें\n2. मतदान केंद्र खोजें\n3. मतदान दिवस पर जाएं और वोट करें",
        "eligible": "**पात्रता जांच:**\nक्या आप नागरिक हैं?",
        "timeline": "चुनाव की समयसीमा अलग-अलग होती है। कृपया अपना देश बताएं।",
        "process": "**चरण 1:** मतदान दिवस से पहले अपने मतदान केंद्र का पता ऑनलाइन जांचें।\nक्या आप जारी रखना चाहते हैं?",
    },
    "Kannada": {
        "default": "ನಮಸ್ಕಾರ! ಚುನಾವಣಾ ಪ್ರಕ್ರಿಯೆಯ ಬಗ್ಗೆ ನಾನು ನಿಮಗೆ ಮಾರ್ಗದರ್ಶನ ನೀಡಬಲ್ಲೆ. ನೀವು ಏನು ತಿಳಿಯಲು ಬಯಸುತ್ತೀರಿ?",
        "register": "**ಹಂತ 1: ಮತದಾರ ನೋಂದಣಿ**\nಮೊದಲು ನಿಮ್ಮ ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ (18+ ಮತ್ತು ನಾಗರಿಕ). ದಾಖಲೆಗಳನ್ನು ಸಿದ್ಧಪಡಿಸಿ ಮತ್ತು ಚುನಾವಣಾ ಕಚೇರಿಯಲ್ಲಿ ನೋಂದಾಯಿಸಿ.\nಮುಂದುವರಿಸಲು ಬಯಸುವಿರಾ?",
        "roadmap": "**ನಿಮ್ಮ ವೈಯಕ್ತಿಕ ರೋಡ್‌ಮ್ಯಾಪ್:**\n1. ನೋಂದಾಯಿತರಲ್ಲದಿದ್ದರೆ → ಅಕ್ಟೋಬರ್ 10 ರ ಮೊದಲು ನೋಂದಾಯಿಸಿ\n2. ಮತದಾನ ಕೇಂದ್ರ ಹುಡುಕಿ\n3. ಮತದಾನ ದಿನ ಹೋಗಿ",
        "eligible": "**ಅರ್ಹತೆ ಪರೀಕ್ಷೆ:**\nನೀವು ನಾಗರಿಕರೇ?",
        "timeline": "ಚುನಾವಣಾ ದಿನಾಂಕಗಳು ಬದಲಾಗುತ್ತವೆ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ದೇಶ ತಿಳಿಸಿ.",
        "process": "**ಹಂತ 1:** ಮತದಾನ ದಿನದ ಮೊದಲು ಮತದಾನ ಕೇಂದ್ರದ ವಿಳಾಸ ಪರಿಶೀಲಿಸಿ.\nಮುಂದುವರಿಸಲು ಬಯಸುವಿರಾ?",
    },
    "Bengali": {
        "default": "নমস্কার! নির্বাচন প্রক্রিয়া সম্পর্কে আমি আপনাকে গাইড করতে পারি। আপনি কী জানতে চান?",
        "register": "**ধাপ ১: ভোটার নিবন্ধন**\nপ্রথমে যোগ্যতা যাচাই করুন (১৮+ এবং নাগরিক)। দলিল সংগ্রহ করুন এবং নির্বাচন অফিসে নিবন্ধন করুন।\nচালিয়ে যেতে চান?",
        "roadmap": "**আপনার ব্যক্তিগত রোডম্যাপ:**\n১. নিবন্ধিত না হলে → ১০ অক্টোবরের আগে নিবন্ধন করুন\n২. ভোটকেন্দ্র খুঁজুন\n৩. ভোটের দিন যান",
        "eligible": "**যোগ্যতা পরীক্ষা:**\nআপনি কি নাগরিক?",
        "timeline": "নির্বাচনের সময়সীমা পরিবর্তিত হয়। আপনার দেশ জানান।",
        "process": "**ধাপ ১:** ভোটের দিনের আগে ভোটকেন্দ্রের ঠিকানা অনলাইনে যাচাই করুন।\nচালিয়ে যেতে চান?",
    },
    "Telugu": {
        "default": "నమస్కారం! ఎన్నికల ప్రక్రియ గురించి నేను మీకు మార్గదర్శనం చేయగలను. మీరు ఏమి తెలుసుకోవాలనుకుంటున్నారు?",
        "register": "**దశ 1: ఓటరు నమోదు**\nముందుగా అర్హత తనిఖీ చేయండి (18+ మరియు పౌరుడు). పత్రాలు సేకరించండి మరియు ఎన్నికల కార్యాలయంలో నమోదు చేయండి.\nకొనసాగించాలనుకుంటున్నారా?",
        "roadmap": "**మీ వ్యక్తిగత రోడ్‌మ్యాప్:**\n1. నమోదు కాకపోతే → అక్టోబర్ 10 లోపు నమోదు చేయండి\n2. పోలింగ్ బూత్ కనుగొనండి\n3. పోలింగ్ రోజున వెళ్ళండి",
        "eligible": "**అర్హత తనిఖీ:**\nమీరు పౌరుడా?",
        "timeline": "ఎన్నికల కాలక్రమం మారుతుంది. మీ దేశం చెప్పండి.",
        "process": "**దశ 1:** పోలింగ్ రోజుకు ముందు పోలింగ్ స్టేషన్ స్థానం ఆన్‌లైన్‌లో తనిఖీ చేయండి.\nకొనసాగించాలనుకుంటున్నారా?",
    },
    "Marathi": {
        "default": "नमस्कार! निवडणूक प्रक्रियेबद्दल मी तुम्हाला मार्गदर्शन करू शकतो. तुम्हाला काय जाणून घ्यायचे आहे?",
        "register": "**पायरी १: मतदार नोंदणी**\nप्रथम पात्रता तपासा (18+ आणि नागरिक). कागदपत्रे जमा करा आणि निवडणूक कार्यालयात नोंदणी करा.\nपुढे चालू ठेवायचे का?",
        "roadmap": "**तुमचा वैयक्तिक रोडमॅप:**\n१. नोंदणी नसल्यास → १० ऑक्टोबरपूर्वी नोंदणी करा\n२. मतदान केंद्र शोधा\n३. मतदान दिवशी जा",
        "eligible": "**पात्रता तपासणी:**\nतुम्ही नागरिक आहात का?",
        "timeline": "निवडणुकीच्या वेळा बदलतात. तुमचा देश सांगा.",
        "process": "**पायरी १:** मतदानाच्या आधी मतदान केंद्राचे ठिकाण ऑनलाइन तपासा.\nपुढे चालू ठेवायचे का?",
    },
    "Tamil": {
        "default": "வணக்கம்! தேர்தல் செயல்முறை பற்றி நான் உங்களுக்கு வழிகாட்ட முடியும். நீங்கள் என்ன தெரிந்துகொள்ள விரும்புகிறீர்கள்?",
        "register": "**படி 1: வாக்காளர் பதிவு**\nமுதலில் தகுதியை சரிபார்க்கவும் (18+ மற்றும் குடிமகன்). ஆவணங்களை சேகரித்து தேர்தல் அலுவலகத்தில் பதிவு செய்யவும்.\nதொடர விரும்புகிறீர்களா?",
        "roadmap": "**உங்கள் தனிப்பயன் வழிகாட்டி:**\n1. பதிவில்லை என்றால் → அக்டோபர் 10க்குள் பதிவு செய்யுங்கள்\n2. வாக்குச்சாவடி கண்டுபிடிக்கவும்\n3. வாக்களிக்கும் நாளில் சென்று வாக்களியுங்கள்",
        "eligible": "**தகுதி சோதனை:**\nநீங்கள் குடிமகனா?",
        "timeline": "தேர்தல் நேர அட்டவணை மாறுபடும். உங்கள் நாட்டை சொல்லுங்கள்.",
        "process": "**படி 1:** வாக்களிக்கும் நாளுக்கு முன் வாக்குச்சாவடி இடத்தை சரிபார்க்கவும்.\nதொடர விரும்புகிறீர்களா?",
    },
}


def fallback_logic(query: str, language: str = "English", history: list = None) -> Tuple[str, List[str]]:
    import re
    if history is None:
        history = []
    q = query.lower().strip()
    lang = TRANSLATIONS.get(language)

    # --- 1. Start Over ---
    if "start over" in q:
        msg = "👋 **Hi! I'm your Election Assistant.**\n\nI can guide you through the complete election process step-by-step.\n\nWhat would you like to learn about today?"
        return msg, _actions_for_phase(0)

    # --- 2. Direct phase targeting from button text (most reliable) ---
    # Handles: "Yes, continue to Phase 2", "Back to Phase 1", "Phase 3", etc.
    phase_match = re.search(r'phase (\d)', q)
    if phase_match:
        target = int(phase_match.group(1))
        if 1 <= target <= 4:
            return PHASE_CONTENT[target], _actions_for_phase(target)

    # --- 3. Generic YES / continue — advance from history ---
    if _detect_yes(q) and language == "English":
        phase = _get_current_phase(history)
        next_phase = phase + 1
        if 1 <= next_phase <= 4:
            return PHASE_CONTENT[next_phase], _actions_for_phase(next_phase)

    # Eligibility check — sequential questions
    if any(k in q for k in ["eligible", "eligibility", "can i vote", "am i eligible", "check eligibility"]):
        step = _get_eligibility_step(history)
        if step < len(ELIGIBILITY_QUESTIONS):
            q_text = ELIGIBILITY_QUESTIONS[step]
            if step == 0:
                return q_text, ["✅ Yes, I am a citizen", "❌ No, I'm not a citizen"]
            if step == 1:
                return q_text, ["✅ Yes, I'm 18+", "❌ No, I'm under 18"]
            if step == 2:
                return q_text, ["✅ Yes, I'm registered", "❌ No, not yet"]
        # All answered — evaluate
        answers = [m.get("user_message", "").lower() for m in history[-3:]]
        is_eligible = all("yes" in a or "✅" in a for a in answers)
        if is_eligible:
            result = "🎉 **Great news! You appear to be eligible to vote!**\n\nYou are a citizen, 18+, and registered. You're all set for Election Day!\n\nWould you like your personalised Voting Roadmap?"
        else:
            result = "ℹ️ **Based on your answers, you may not yet be fully eligible.**\n\nYou may need to:\n• Register to vote if you haven't already\n• Ensure you meet age and citizenship requirements\n\nWould you like help with voter registration?"
        return result, ["🗺️ My Voting Roadmap", "📋 Register to Vote", "🏠 Start Over"]

    # Roadmap
    if any(k in q for k in ["roadmap", "should i do", "what to do", "my voting roadmap"]):
        if lang:
            return lang["roadmap"], ["📍 Find My Polling Booth", "✅ Check Eligibility", "🏠 Start Over"]
        roadmap = "**🗺️ Your Personalised Voting Roadmap:**\n\n✅ **Step 1:** Check your eligibility (18+ and a citizen)\n✅ **Step 2:** Register to vote before the deadline\n✅ **Step 3:** Find your polling location online\n✅ **Step 4:** Review candidates and ballot measures\n✅ **Step 5:** Go to your polling station on Election Day with your ID\n✅ **Step 6:** Cast your vote!\n\n🎯 You've got this!"
        return roadmap, ["📍 Find My Polling Booth", "✅ Check Eligibility", "🏠 Start Over"]

    # Register
    if "register" in q:
        if lang:
            return lang["register"], ["✅ Yes, continue!", "🔄 Start Over"]
        return PHASE_CONTENT[1], _actions_for_phase(1)

    # Timeline / dates
    if any(k in q for k in ["timeline", "date", "when", "deadline"]):
        if lang:
            return lang["timeline"], ["📋 Register to Vote", "🗳️ Voting Process", "🔄 Start Over"]
        return "📅 **Election Timelines vary by region.**\n\nGeneral phases:\n• **Voter Registration Deadline** — Usually 15-30 days before election\n• **Early Voting Period** — 1-2 weeks before Election Day\n• **Election Day** — The official voting date\n• **Results** — Announced within hours to days after polls close\n\nPlease check your local election authority website for exact dates.", ["📋 Register to Vote", "🗳️ Voting Process", "🔄 Start Over"]

    # Process / how to vote
    if any(k in q for k in ["process", "step", "how to vote", "voting process"]):
        if lang:
            return lang["process"], ["✅ Yes, continue!", "🔄 Start Over"]
        return PHASE_CONTENT[1], _actions_for_phase(1)

    # Default
    if lang:
        return lang["default"], _actions_for_phase(0)
    return "👋 **Hi! I'm your Election Assistant.**\n\nI can guide you through the complete election process step-by-step.\n\nWhat would you like to learn about today?", _actions_for_phase(0)


def process_chat_message(
    session_id: str,
    user_message: str,
    location: str = "General (No specific region)",
    language: str = "English",
) -> Tuple[str, bool, List[str]]:
    # 1. Security Check
    has_pii, warning_msg = scan_for_pii(user_message)
    if has_pii:
        return warning_msg, True, ["🔄 Ask a different question", "🏠 Start Over"]

    # 2. Process with AI or Fallback
    global client
    if client is None:
        gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        if gemini_api_key:
            try:
                client = genai.Client(api_key=gemini_api_key)
            except Exception as e:
                logger.warning("Gemini client init failed: %s", e)

    history = get_chat_history(session_id)
    response_text = ""
    suggested_actions = []

    try:
        if client:
            history_context = ""
            for msg in history:
                history_context += f"User: {msg['user_message']}\nAssistant: {msg['assistant_message']}\n"
            context = (
                f"{SYSTEM_PROMPT}\n\nUSER'S LOCATION: {location}\nUSER'S LANGUAGE: {language}\n\n"
                f"CONVERSATION HISTORY:\n{history_context}\n\n"
                f"Respond entirely in {language}. End with a clear question.\n\nUser: {user_message}"
            )
            response = client.models.generate_content(model="gemini-flash-latest", contents=context)
            response_text = response.text
            suggested_actions = get_suggested_actions(response_text)
        else:
            response_text, suggested_actions = fallback_logic(user_message, language, history)
            if not client:
                response_text += "\n\n*(Using local mode — add GEMINI_API_KEY for full AI responses)*"
    except Exception as e:
        logger.error("Gemini error: %s", e)
        response_text, suggested_actions = fallback_logic(user_message, language, history)

    save_chat_message(session_id, user_message, response_text)
    return response_text, False, suggested_actions
