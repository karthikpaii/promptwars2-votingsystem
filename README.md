# 🗳️ Election Assistant — Secure Voting Guide Powered by Gemini AI

> **Built with Antigravity as part of the Google Promptwars Hackathon — Challenge 2**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Cloud%20Run-blue?logo=google-cloud)](https://election-assistant-155727688265.us-central1.run.app)
[![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey?logo=flask)](https://flask.palletsprojects.com/)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI-orange?logo=google)](https://ai.google.dev/)
[![Google Cloud Run](https://img.shields.io/badge/Deployed-Cloud%20Run-4285F4?logo=google-cloud)](https://cloud.google.com/run)

---

## 🌐 Live Demo

**👉 [https://election-assistant-155727688265.us-central1.run.app](https://election-assistant-155727688265.us-central1.run.app)**

---

## 📖 About

**Election Assistant** is an AI-powered, multilingual chatbot that helps citizens navigate the election process step by step. Whether you're a first-time voter or need a refresher, the assistant guides you through voter registration, eligibility checks, voting procedures, and personalized roadmaps — all in your preferred language.

Built with **Google Gemini AI** at its core, it ensures every response is neutral, verified, and secure. Sensitive information like SSNs, Aadhaar numbers, and passwords are automatically detected and blocked.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI-Powered Chat** | Gemini AI answers election questions with step-by-step guidance |
| 🌍 **Multilingual Support** | Supports English, Hindi, Kannada, Bengali, Telugu, Marathi, and Tamil |
| 📍 **Region-Aware** | Tailors answers based on your selected region (India, USA states, UK) |
| ✅ **Eligibility Checker** | Interactive Q&A mode to determine if you can vote |
| 🗺️ **Personalized Roadmap** | Generates a custom voting checklist based on your situation |
| 📅 **Election Timeline** | Visual timeline of the 4 phases of an election |
| 🔔 **Email Alerts** | Subscribe to get reminders for voter registration deadlines |
| 🔊 **Voice Guidance** | Text-to-speech in all supported languages |
| 🔒 **PII Protection** | Automatically warns and blocks sharing of sensitive personal data |
| ⚡ **Offline Fallback** | Works even without an API key using built-in local logic |

---

## 🧠 How It Works

```
User Message
     │
     ▼
┌─────────────────────┐
│   PII Security Scan │  ← Blocks SSN, Aadhaar, passwords
└─────────────────────┘
     │
     ▼
┌─────────────────────┐
│  Gemini Flash API   │  ← Generates context-aware, region-specific answer
│  (with history)     │     in the user's chosen language
└─────────────────────┘
     │ (API unavailable?)
     ▼
┌─────────────────────┐
│   Local Fallback    │  ← Built-in multilingual logic as backup
└─────────────────────┘
     │
     ▼
  Response sent to UI + saved to MockDB / Firestore
```

---

## 🏗️ Tech Stack

- **Backend:** Python, Flask
- **AI:** Google Gemini AI (`gemini-flash-latest`) via `google-genai` SDK
- **Frontend:** Vanilla HTML, CSS, JavaScript
- **Database:** Google Firestore (with a local `MockDB` fallback)
- **Deployment:** Google Cloud Run (Docker container)
- **Fonts:** Google Fonts (Inter)

---

## 🚀 Run Locally

### Prerequisites
- Python 3.10+
- A Google Gemini API Key ([Get one free here](https://ai.google.dev/))

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/karthikpaii/promptwars2-votingsystem.git
cd promptwars2-votingsystem/Voting\ System

# 2. Create a virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your environment variables
# Edit the .env file with your own key:
# GEMINI_API_KEY=your_api_key_here
# SECRET_KEY=your_secret_key

# 5. Run the app
python app.py
```

Open your browser and navigate to **[http://127.0.0.1:8080](http://127.0.0.1:8080)**

---

## ☁️ Deploy to Google Cloud Run

Make sure you have the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed and are logged in.

```bash
gcloud run deploy election-assistant \
  --source "Voting System" \
  --project YOUR_PROJECT_ID \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=your_key,SECRET_KEY=your_secret"
```

---

## 📁 Project Structure

```
Voting System/
├── app.py                  # Flask application entry point
├── Dockerfile              # Container config for Cloud Run
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not committed)
├── services/
│   ├── conversation.py     # Gemini AI logic, system prompt, fallback
│   ├── db.py               # Firestore + MockDB adapter
│   └── security.py         # PII detection and filtering
├── templates/
│   └── index.html          # Main chat UI
└── static/
    ├── style.css           # App styling
    └── app.js              # Frontend logic, voice, modals
```

---

## 🌏 Supported Languages

| Language | Voice Code |
|---|---|
| English | `en-US` |
| हिंदी (Hindi) | `hi-IN` |
| ಕನ್ನಡ (Kannada) | `kn-IN` |
| বাংলা (Bengali) | `bn-IN` |
| తెలుగు (Telugu) | `te-IN` |
| मराठी (Marathi) | `mr-IN` |
| தமிழ் (Tamil) | `ta-IN` |

---

## 🔒 Security

- **No personal data is stored** — the chat history is session-scoped and in-memory by default
- **PII Scanner** actively prevents users from accidentally sharing SSNs, Aadhaar numbers, or passwords
- **Neutral & Non-political** — the AI is strictly instructed to provide factual, unbiased election information only

---

## 👨‍💻 Built By

**Karthik Pai** — Built with ❤️ and [Antigravity](https://antigravity.dev) for the **Google Promptwars Hackathon 2026**

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
