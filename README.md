📝 Selfloom - Journaling & AI Assistant
A smart journaling application with AI assistant for mental health and personal growth.

✨ Key Features
📓 Smart Journaling: Write journals with automatic mood analysis

🤖 AI Assistant: Chat with an empathetic AI for mental support

📊 Mood Tracking: Track emotional patterns with color visualization

🗄️ Private Storage: Data securely stored in local database

🚀 Quick Start
1. Install Dependencies
bash
pip install streamlit google-generativeai sqlalchemy pymysql python-dotenv
2. Setup Environment
Create .env file:

env
GOOGLE_API_KEY=your_gemini_api_key_here
3. Run App
bash
streamlit run selfloom_app.py
🎯 How to Use
Journaling Tab: Write daily journals, mood will be automatically analyzed

AI Assistant Tab: Chat with AI for counseling & emotional support

History Tab: View journal history and delete if needed

🔧 Configuration
Get Gemini API key from Google AI Studio

Database will be automatically created (SQLite) if MySQL is not available.

⚠️ Disclaimer
Selfloom is an AI assistant, not a replacement for mental health professionals. For serious conditions, contact qualified experts.

Made with ❤️ for better mental health

