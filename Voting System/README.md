# 🗳️ Secure Election Assistant

A powerful, intelligent, and multilingual assistant designed to guide voters through every step of the electoral process. Built for the **Prompt Wars 2.0 Hackathon**, this tool ensures that verified, secure, and accessible voting information is available to everyone, regardless of their language.

[![Live Demo](https://img.shields.io/badge/Live-Demo-blue?style=for-the-badge)](https://election-assistant-155727688265.us-central1.run.app)
[![Tests](https://img.shields.io/badge/Tests-59%20Passed-green?style=for-the-badge)]()
[![Code Quality](https://img.shields.io/badge/Code%20Quality-100%25-brightgreen?style=for-the-badge)]()

## 🌟 Key Features

-   **🌍 Multilingual Support**: Comprehensive step-by-step guidance in **English, Hindi, Kannada, Bengali, Telugu, Marathi, and Tamil**.
-   **🔒 Secure by Design**: 
    -   Integrated **PII Scanner** to prevent sensitive data (Aadhaar, SSN, Passwords) from being processed.
    -   Strict security headers and sanitized inputs.
-   **✅ Phased Guidance**: Breaks down the complex voting process into 4 manageable phases:
    1.  Voter Registration
    2.  Preparation & Research
    3.  Casting Your Vote
    4.  Result Declaration
-   **🗺️ Personalised Roadmap**: Generates a custom checklist for voters based on their current progress.
-   **📅 Election Timelines**: Real-time information on registration deadlines and election dates.
-   **🤖 Gemini AI Integration**: Leverages Google's `gemini-flash-latest` for natural, context-aware conversations.

## 🛠️ Tech Stack

-   **Backend**: Python / Flask
-   **AI**: Google Gemini Pro (via `google-genai`)
-   **Database**: Google Cloud Firestore (with local MockDB fallback)
-   **Infrastructure**: Docker / Google Cloud Run
-   **Frontend**: Vanilla HTML5/CSS3/JS (Modern Inter UI)

## 🚀 Quick Start

### Prerequisites
-   Python 3.11+
-   Google Cloud Project (optional)
-   Gemini API Key

### Local Installation
1.  **Clone the repository**:
    ```bash
    git clone https://github.com/karthikpaii/promptwars2-votingsystem.git
    cd "Voting System"
    ```
2.  **Set up virtual environment**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Environment**:
    Create a `.env` file:
    ```env
    GEMINI_API_KEY=your_key_here
    FLASK_ENV=development
    ```
5.  **Run the app**:
    ```bash
    python app.py
    ```

## 🧪 Testing

The project maintains a **100% pass rate** across its extensive test suite.

```bash
# Run all tests
pytest tests/

# Check coverage
pytest tests/ --cov=services --cov=app
```

## ☁️ Deployment

The app is containerized and ready for **Google Cloud Run**:

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/election-assistant
gcloud run deploy --image gcr.io/YOUR_PROJECT_ID/election-assistant --platform managed
```

## 📄 License
This project is part of the Prompt Wars 2.0 Hackathon. All rights reserved.

---
**Secure Election Assistant** — *Empowering every voice, in every language.*
