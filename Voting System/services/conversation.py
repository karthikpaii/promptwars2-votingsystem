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

def fallback_logic(query, language="English"):
    query = query.lower()
    
    # Translations for common responses
    translations = {
        "Hindi": {
            "default": "नमस्ते! मैं चुनाव प्रक्रिया में आपका मार्गदर्शन कर सकता हूँ। आप आज क्या सीखना चाहेंगे?",
            "register": "चरण 1: अपने क्षेत्र के आधार पर मतदान करने के लिए अपनी पात्रता जांचें।\nक्या आप जारी रखना चाहते हैं?",
            "timeline": "चुनाव की समयसीमा अलग-अलग होती है। कृपया मुझे अपना देश या राज्य बताएं।\nक्या आप जारी रखना चाहते हैं?",
            "process": "चरण 1: मतदान के दिन से पहले, अपने मतदान केंद्र का स्थान ऑनलाइन सत्यापित करें।\nक्या आप जारी रखना चाहते हैं?",
            "eligible": "चरण 1: अधिकांश स्थानों पर, मतदान करने के लिए आपकी आयु कम से कम 18 वर्ष होनी चाहिए।\nक्या आप जारी रखना चाहते हैं?",
            "roadmap": "आपका व्यक्तिगत रोडमैप:\n1. यदि आप पंजीकृत नहीं हैं -> 10 अक्टूबर से पहले पंजीकरण करें।\n2. यदि आप पंजीकृत हैं -> अपना मतदान केंद्र खोजें।"
        },
        "Kannada": {
            "default": "ನಮಸ್ಕಾರ! ಚುನಾವಣಾ ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿ ನಾನು ನಿಮಗೆ ಮಾರ್ಗದರ್ಶನ ನೀಡಬಲ್ಲೆ. ನೀವು ಇಂದು ಏನನ್ನು ಕಲಿಯಲು ಬಯಸುತ್ತೀರಿ?",
            "register": "ಹಂತ 1: ನಿಮ್ಮ ಪ್ರದೇಶದ ಆಧಾರದ ಮೇಲೆ ಮತದಾನ ಮಾಡಲು ನಿಮ್ಮ ಅರ್ಹತೆಯನ್ನು ಪರಿಶೀಲಿಸಿ.\nನೀವು ಮುಂದುವರಿಸಲು ಬಯಸುವಿರಾ?",
            "timeline": "ಚುನಾವಣಾ ಸಮಯದ ಮಿತಿಗಳು ಬದಲಾಗುತ್ತವೆ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ದೇಶ ಅಥವಾ ರಾಜ್ಯವನ್ನು ನನಗೆ ತಿಳಿಸಿ.\nನೀವು ಮುಂದುವರಿಸಲು ಬಯಸುವಿರಾ?",
            "process": "ಹಂತ 1: ಮತದಾನದ ದಿನದ ಮೊದಲು, ನಿಮ್ಮ ಮತದಾನ ಕೇಂದ್ರದ ಸ್ಥಳವನ್ನು ಆನ್‌ಲೈನ್‌ನಲ್ಲಿ ಪರಿಶೀಲಿಸಿ.\nನೀವು ಮುಂದುವರಿಸಲು ಬಯಸುವಿರಾ?",
            "eligible": "ಹಂತ 1: ಹೆಚ್ಚಿನ ಸ್ಥಳಗಳಲ್ಲಿ, ಮತದಾನ ಮಾಡಲು ನಿಮಗೆ ಕನಿಷ್ಠ 18 ವರ್ಷ ವಯಸ್ಸಾಗಿರಬೇಕು.\nನೀವು ಮುಂದುವರಿಸಲು ಬಯಸುವಿರಾ?",
            "roadmap": "ನಿಮ್ಮ ವೈಯಕ್ತಿಕ ಮಾರ್ಗಸೂಚಿ:\n1. ನೀವು ನೋಂದಾಯಿತರಲ್ಲದಿದ್ದರೆ -> ಅಕ್ಟೋಬರ್ 10 ರ ಮೊದಲು ನೋಂದಾಯಿಸಿ.\n2. ನೀವು ನೋಂದಾಯಿತರಾಗಿದ್ದರೆ -> ನಿಮ್ಮ ಮತದಾನದ ಬೂತ್ ಅನ್ನು ಹುಡುಕಿ."
        },
        "Bengali": {
            "default": "নমস্কার! আমি আপনাকে নির্বাচনী প্রক্রিয়ার মাধ্যমে নির্দেশিকা দিতে পারি। আপনি আজ কি জানতে চান?",
            "register": "ধাপ ১: আপনার অঞ্চলের উপর ভিত্তি করে ভোট দেওয়ার জন্য আপনার যোগ্যতা যাচাই করুন।\nআপনি কি চালিয়ে যেতে চান?",
            "timeline": "নির্বাচনের সময়সীমা পরিবর্তিত হয়। দয়া করে আমাকে আপনার দেশ বা রাজ্য বলুন।\nআপনি কি চালিয়ে যেতে চান?",
            "process": "ধাপ ১: ভোটগ্রহণের দিনের আগে, আপনার ভোটকেন্দ্রের অবস্থান অনলাইনে যাচাই করুন।\nআপনি কি চালিয়ে যেতে চান?",
            "eligible": "ধাপ ১: অধিকাংশ স্থানে, ভোট দেওয়ার জন্য আপনার বয়স কমপক্ষে ১৮ বছর হতে হবে।\nআপনি কি চালিয়ে যেতে চান?",
            "roadmap": "আপনার ব্যক্তিগত রোডম্যাপ:\n১. যদি আপনি নিবন্ধিত না হন -> ১০ অক্টোবরের আগে নিবন্ধন করুন।\n২. যদি আপনি নিবন্ধিত হন -> আপনার পোলিং বুথ খুঁজুন।"
        },
        "Telugu": {
            "default": "నమస్కారం! నేను మీకు ఎన్నికల ప్రక్రియ ద్వారా మార్గనిర్దేశం చేయగలను. మీరు ఈరోజు ఏమి తెలుసుకోవాలనుకుంటున్నారు?",
            "register": "దశ 1: మీ ప్రాంతం ఆధారంగా ఓటు వేయడానికి మీ అర్హతను తనిఖీ చేయండి.\nమీరు కొనసాగించాలనుకుంటున్నారా?",
            "timeline": "ఎన్నికల కాలక్రమం మారుతూ ఉంటుంది. దయచేసి మీ దేశం లేదా రాష్ట్రం చెప్పండి.\nమీరు కొనసాగించాలనుకుంటున్నారా?",
            "process": "దశ 1: ఓటింగ్ రోజుకు ముందు, మీ పోలింగ్ స్టేషన్ స్థానాన్ని ఆన్‌లైన్‌లో ధృవీకరించుకోండి.\nమీరు కొనసాగించాలనుకుంటున్నారా?",
            "eligible": "దశ 1: చాలా చోట్ల, ఓటు వేయడానికి మీకు కనీసం 18 ఏళ్లు నిండి ఉండాలి.\nమీరు కొనసాగించాలనుకుంటున్నారా?",
            "roadmap": "మీ వ్యక్తిగత రోడ్‌మ్యాప్:\n1. మీరు నమోదు చేసుకోకపోతే -> అక్టోబర్ 10 లోపు నమోదు చేసుకోండి.\n2. మీరు నమోదు చేసుకున్నట్లయితే -> మీ పోలింగ్ బూత్‌ను కనుగొనండి."
        },
        "Marathi": {
            "default": "नमस्कार! मी तुम्हाला निवडणूक प्रक्रियेद्वारे मार्गदर्शन करू शकतो. तुम्हाला आज काय शिकायला आवडेल?",
            "register": "पायरी १: तुमच्या प्रदेशानुसार मतदान करण्यासाठी तुमची पात्रता तपासा.\nतुम्हाला पुढे चालू ठेवायचे आहे का?",
            "timeline": "निवडणुकीच्या वेळापत्रकात बदल होऊ शकतात. कृपया मला तुमचा देश किंवा राज्य सांगा.\nतुम्हाला पुढे चालू ठेवायचे आहे का?",
            "process": "पायरी १: मतदानाच्या दिवसापूर्वी, तुमच्या मतदान केंद्राचे ठिकाण ऑनलाइन तपासा.\nतुम्हाला पुढे चालू ठेवायचे आहे का?",
            "eligible": "पायरी १: बहुतेक ठिकाणी, मतदान करण्यासाठी तुमचे वय किमान १८ वर्षे असणे आवश्यक आहे.\nतुम्हाला पुढे चालू ठेवायचे आहे का?",
            "roadmap": "तुमचा वैयक्तिक रोडमॅप:\n१. तुम्ही नोंदणीकृत नसल्यास -> १० ऑक्टोबरपूर्वी नोंदणी करा.\n२. तुम्ही नोंदणीकृत असल्यास -> तुमचे मतदान केंद्र शोधा."
        },
        "Tamil": {
            "default": "வணக்கம்! தேர்தல் செயல்முறை மூலம் நான் உங்களுக்கு வழிகாட்ட முடியும். இன்று நீங்கள் எதைப் பற்றி தெரிந்து கொள்ள விரும்புகிறீர்கள்?",
            "register": "படி 1: உங்கள் பிராந்தியத்தின் அடிப்படையில் வாக்களிக்க உங்கள் தகுதியைச் சரிபார்க்கவும்.\nதொடர விரும்புகிறீர்களா?",
            "timeline": "தேர்தல் காலக்கெடு மாறுபடும். தயவுசெய்து உங்கள் நாடு அல்லது மாநிலத்தைச் சொல்லுங்கள்.\nதொடர விரும்புகிறீர்களா?",
            "process": "படி 1: வாக்களிக்கும் நாளுக்கு முன்னதாக, உங்கள் வாக்குச்சாவடி இருப்பிடத்தை ஆன்லைனில் சரிபார்க்கவும்.\nதொடர விரும்புகிறீர்களா?",
            "eligible": "படி 1: பெரும்பாலான இடங்களில், வாக்களிக்க உங்களுக்கு குறைந்தபட்சம் 18 வயது பூர்த்தியாகியிருக்க வேண்டும்.\nதொடர விரும்புகிறீர்களா?",
            "roadmap": "உங்கள் தனிப்பயனாக்கப்பட்ட சாலை வரைபடம்:\n1. நீங்கள் பதிவு செய்யவில்லை என்றால் -> அக்டோபர் 10-க்குள் பதிவு செய்யவும்.\n2. நீங்கள் பதிவு செய்திருந்தால் -> உங்கள் வாக்குச்சாவடியைக் கண்டறியவும்."
        }
    }

    lang_data = translations.get(language)
    
    if "roadmap" in query or "should i do" in query or "what to do" in query:
        return lang_data["roadmap"] if lang_data else "Your Personalized Roadmap:\n1. If you are not registered -> Register before Oct 10.\n2. If you are registered -> Find your polling booth."
    if "register" in query:
        return lang_data["register"] if lang_data else "Step 1: Check your eligibility to vote based on your region.\nDo you want to continue?"
    if "timeline" in query or "date" in query or "when" in query:
        return lang_data["timeline"] if lang_data else "Election timelines vary by country. Please tell me your country or state.\nDo you want to continue?"
    if "process" in query or "step" in query or "how to vote" in query:
        return lang_data["process"] if lang_data else "Step 1: Before voting day, verify your polling station location online.\nDo you want to continue?"
    if "rule" in query or "eligibility" in query or "eligible" in query:
        return lang_data["eligible"] if lang_data else "Step 1: In most places, you must be at least 18 years old and a citizen to vote.\nDo you want to continue?"
    
    return lang_data["default"] if lang_data else "Hi! I can guide you through the election process. What would you like to learn?"

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
            response_text = fallback_logic(user_message, language) + "\n\n*(Using local logic - set GEMINI_API_KEY for full AI power)*"
    except Exception as e:
        print(f"Gemini Error: {e}")
        response_text = fallback_logic(user_message, language)

    # 3. Database Write (Telemetry/Context)
    save_chat_message(session_id, user_message, response_text)

    return response_text, False
