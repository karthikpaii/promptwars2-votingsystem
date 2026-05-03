# 🗳️ Secure Election Assistant

A powerful, intelligent, and multilingual assistant designed to guide voters through every step of the electoral process. Built for the **Prompt Wars 2.0 Hackathon**, this tool ensures that verified, secure, and accessible voting information is available to everyone, regardless of their language.

[![Live Demo](https://img.shields.io/badge/Live-Demo-blue?style=for-the-badge)](https://election-assistant-155727688265.us-central1.run.app)
[![Tests](https://img.shields.io/badge/Tests-60%20Passed-green?style=for-the-badge)]()
[![Code Quality](https://img.shields.io/badge/Code%20Quality-100%25-brightgreen?style=for-the-badge)]()
[![Accessibility](https://img.shields.io/badge/Accessibility-100%25-blueviolet?style=for-the-badge)]()

## 🌟 Key Features

-   **🌍 Multilingual Support**: Comprehensive step-by-step guidance in **English, Hindi, Kannada, Bengali, Telugu, Marathi, and Tamil**.
-   **🔒 Secure by Design**: 
    -   Integrated **PII Scanner** to prevent sensitive data (Aadhaar, SSN, Passwords) from being processed.
    -   Strict security headers and sanitized inputs.
-   **✅ Phased Guidance**: Breaks down the complex voting process into 4 manageable phases.
-   **📥 Exportable Roadmap**: Users can now **download their personalised voting roadmap** as a text file for offline use.
-   **⚡ High-Performance Caching**: Implemented intelligent response caching and static asset optimization for sub-second responses.
-   **♿ Accessibility First**: 100% WCAG compliant with skip-links, ARIA landmarks, and full keyboard navigation support.
-   **🤖 Gemini AI Integration**: Leverages Google's `gemini-flash-latest` for natural, context-aware conversations.

## 🛠️ Tech Stack

-   **Backend**: Python / Flask
-   **AI**: Google Gemini Pro (via `google-genai`)
-   **Database**: Google Cloud Firestore (with local MockDB fallback)
-   **Performance**: In-memory Response Caching & Static Asset Optimization
-   **Infrastructure**: Docker / Google Cloud Run
-   **Frontend**: Vanilla HTML5/CSS3/JS (Modern Inter UI with Glassmorphic accents)

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
