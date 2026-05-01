import pytest
from services.conversation import fallback_logic, _detect_yes, _get_current_phase

def test_detect_yes_multilingual():
    assert _detect_yes("yes") is True
    assert _detect_yes("हां") is True  # Hindi
    assert _detect_yes("ಹೌದು") is True # Kannada
    assert _detect_yes("no") is False

def test_fallback_logic_hindi():
    query = "पंजीकरण" # Register in Hindi (one of the keywords)
    response, actions = fallback_logic(query, language="Hindi")
    assert "चरण 1: मतदाता पंजीकरण" in response
    assert "✅ Yes, continue to Phase 2" in actions

def test_fallback_logic_kannada():
    query = "ನೋಂದಣಿ" # Register in Kannada
    response, actions = fallback_logic(query, language="Kannada")
    assert "ಹಂತ 1: ಮತದಾರರ ನೋಂದಣಿ" in response

def test_phase_transition_multilingual():
    history = [{"user_message": "start", "assistant_message": "🗳️ **चरण 1: मतदाता पंजीकरण**"}]
    # User says "yes" in Hindi
    response, actions = fallback_logic("हां", language="Hindi", history=history)
    assert "चरण 2: तैयारी" in response
    assert "✅ Yes, continue to Phase 3" in actions

def test_roadmap_multilingual():
    response, _ = fallback_logic("roadmap", language="Telugu")
    assert "మీ వ్యక్తిగత రోడ్‌మ్యాప్" in response

def test_eligibility_multilingual():
    # Question 1 in Tamil
    response, actions = fallback_logic("eligibility", language="Tamil")
    assert "தகுதிச் சரிபார்ப்பு — கேள்வி 1/3" in response
    assert "✅ Yes" in actions

def test_fallback_logic_invalid_lang():
    # Should default to English
    response, _ = fallback_logic("register", language="French")
    assert "Phase 1: Voter Registration" in response
