import streamlit as st
from datetime import date
import os
import sys
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Date, Text
from sqlalchemy.orm import sessionmaker
from sqlalchemy import delete
import traceback

# Load Environment Variables dari .env

try:
    from dotenv import load_dotenv
    load_dotenv()
    st.sidebar.success("File .env berhasil dimuat")
except ImportError:
    st.sidebar.warning(" python-dotenv tidak terinstall")

# Import Google Generative AI

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    st.error("Library google-generativeai tidak terinstall! Jalankan: `pip install google-generativeai`")
    st.stop()

# Konfigurasi API Key Gemini

GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GEMINI_API_KEY:
    st.error("GOOGLE_API_KEY tidak ditemukan!")
    st.stop()

try:
    genai.configure(api_key=GEMINI_API_KEY)
    CHAT_MODEL = 'gemini-2.0-flash'  
    MOOD_MODEL = 'gemini-2.0-flash'  
    
    st.sidebar.success(f"🤖 Model: {CHAT_MODEL}")
    GEMINI_WORKING = True
    
except Exception as e:
    st.error(f" Gagal mengkonfigurasi Gemini API: {e}")
    st.stop()

# Setup Database

def get_database_config():
    config = {
        'DB_USER': os.getenv('DB_USER', 'selfloom_user'),
        'DB_PASS': os.getenv('DB_PASS', 'SuperSecretPass'), 
        'DB_HOST': os.getenv('DB_HOST', 'localhost'),
        'DB_NAME': os.getenv('DB_NAME', 'selfloom_db')
    }
    return config

db_config = get_database_config()

try:
    DATABASE_URL = f"mysql+pymysql://{db_config['DB_USER']}:{db_config['DB_PASS']}@{db_config['DB_HOST']}/{db_config['DB_NAME']}"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    metadata = MetaData()
    Session = sessionmaker(bind=engine)
    session = Session()

    journal_entries = Table(
        "journal_entries", metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", Integer, nullable=False),
        Column("entry_date", Date, nullable=False),
        Column("content", Text, nullable=False),
        Column("mood", String(50), nullable=True)
    )
    metadata.create_all(engine)
    
except Exception as e:
    DATABASE_URL = "sqlite:///selfloom_temp.db"
    engine = create_engine(DATABASE_URL)
    metadata = MetaData()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    journal_entries = Table(
        "journal_entries", metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", Integer, nullable=False),
        Column("entry_date", Date, nullable=False),
        Column("content", Text, nullable=False),
        Column("mood", String(50), nullable=True)
    )
    metadata.create_all(engine)

# Fungsi Journaling

def analyze_mood(text):
    if not text or len(text.strip()) < 10:
        return "Netral"
    
    prompt = f"""
    Analisis mood dari teks jurnal berikut dan pilih salah satu kategori: 
    Bahagia, Sedih, Marah, Cemas, Netral.
    
    Teks: {text}
    
    Jawab hanya dengan satu kata (mood yang terdeteksi):
    """
    
    try:
        model = genai.GenerativeModel(MOOD_MODEL)
        response = model.generate_content(prompt)
        mood_text = response.text.strip()
        valid_moods = ["Bahagia", "Sedih", "Marah", "Cemas", "Netral"]
        
        for valid_mood in valid_moods:
            if valid_mood.lower() in mood_text.lower():
                return valid_mood
        return "Netral"
        
    except Exception as e:
        st.sidebar.error(f"Error analisis mood: {e}")
        return "Netral"

def add_journal_entry(user_id, content):
    try:
        today = date.today()
        mood = analyze_mood(content)
        
        ins = journal_entries.insert().values(
            user_id=user_id,
            entry_date=today,
            content=content,
            mood=mood
        )
        session.execute(ins)
        session.commit()
        
        mood_emojis = {
            "Bahagia": "😊", "Sedih": "😢", "Marah": "😠", 
            "Cemas": "😰", "Netral": "😐"
        }
        emoji = mood_emojis.get(mood, "😐")
        
        st.success(f"Jurnal berhasil disimpan! {emoji} Mood terdeteksi: **{mood}**")
        return True
        
    except Exception as e:
        st.error(f"Gagal menyimpan jurnal: {e}")
        session.rollback()
        return False

def delete_journal_entry(entry_id):
    try:
        del_stmt = delete(journal_entries).where(journal_entries.c.id == entry_id)
        session.execute(del_stmt)
        session.commit()
        return True
    except Exception as e:
        st.error(f" Gagal menghapus jurnal: {e}")
        session.rollback()
        return False

# Fungsi Chatbot Canggih

def chat_with_gemini(user_message, chat_history=None):
    """Fungsi chatbot canggih seperti GPT"""
    
    system_prompt = """
Anda adalah Selfloom AI - asisten AI yang sangat pintar, empatik, dan helpful untuk aplikasi journaling dan kesehatan mental.

KEMAMPUAN ANDA:
1. 🧠 **Konseling & Dukungan Emosional**: Memberikan dukungan psikologis, mendengarkan aktif, dan saran untuk mengelola emosi
2. 📝 **Expert Journaling**: Ahli dalam teknik menulis jurnal, refleksi diri, dan eksplorasi perasaan
3. 💡 **Problem Solving**: Membantu menganalisis masalah dan menemukan solusi praktis
4. 🎯 **Goal Setting**: Membantu menetapkan tujuan personal dan langkah-langkah mencapainya
5. 🌱 **Personal Growth**: Memberikan wawasan untuk pengembangan diri dan peningkatan kualitas hidup
6. 🏥 **Mental Health Support**: Memberikan edukasi tentang kesehatan mental (dengan disclaimer)
7. 🔍 **Analisis Mendalam**: Menganalisis situasi dari berbagai perspektif

GAYA RESPON:
- Hangat, empatik, dan manusiawi
- Informatif dan berbasis evidence
- Memberikan solusi praktis dan actionable
- Menggunakan bahasa Indonesia yang natural
- Tidak terlalu formal, seperti berbicara dengan teman yang peduli

DISCLAIMER: Ingatkan user untuk konsultasi dengan profesional jika perlu.
"""
    
    try:
        model = genai.GenerativeModel(CHAT_MODEL)
        conversation = system_prompt + "\n\n"
        
        if chat_history:
            for msg in chat_history[-6:]: 
                role = "User" if msg['role'] == 'user' else "Assistant"
                conversation += f"{role}: {msg['content']}\n\n"
        
        conversation += f"User: {user_message}\n\nAssistant:"
        
        response = model.generate_content(
            conversation,
            generation_config=genai.types.GenerationConfig(
                temperature=0.8,
                max_output_tokens=1000,
                top_p=0.9
            )
        )
        
        return response.text.strip()
        
    except Exception as e:
        
        fallback_responses = {
            "cape": "Saya memahami Anda merasa cape dengan tugas. Coba bagi tugas besar menjadi bagian kecil, istirahat sejenak, dan kerjakan satu per satu. Anda bisa melakukannya! 💪",
            "stres": "Stres dengan tugas itu wajar. Coba teknik Pomodoro: kerja 25 menit, istirahat 5 menit. Jangan lupa bernapas dalam dan minum air. 🌿",
            "lelah": "Saya dengar Anda lelah. Istirahat yang cukup penting. Coba tidur 7-8 jam, makan bergizi, dan beri diri waktu untuk recover. 🛌"
        }
        
        user_msg_lower = user_message.lower()
        for keyword, response in fallback_responses.items():
            if keyword in user_msg_lower:
                return response
                
        return "Halo! Saya memahami perasaan Anda. Mari kita bicara lebih lanjut tentang apa yang membuat Anda merasa seperti ini. Ceritakan lebih detail, saya di sini untuk mendengarkan dan membantu! 🤗"


# Streamlit UI

st.set_page_config(
    page_title="Selfloom - Journaling & AI Assistant",
    page_icon="📝", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #d63384;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
    }
    .journal-entry {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1.5rem;
        border-left: 6px solid;
        box-shadow: 0 4px 12px rgba(214, 51, 132, 0.08);
        color: #000000;
    }
    .mood-bahagia { border-left-color: #ec4899; background: #fdf2f8; }
    .mood-sedih { border-left-color: #d946ef; background: #faf5ff; }
    .mood-marah { border-left-color: #db2777; background: #fef1f7; }
    .mood-cemas { border-left-color: #be185d; background: #fdf2f8; }
    .mood-netral { border-left-color: #9d174d; background: #f8fafc; }
    
    /* Chatbot Styles */

    .user-message {
        background: linear-gradient(135deg, #ec4899, #db2777);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 18px;
        margin: 0.8rem 0;
        max-width: 85%;
        margin-left: auto;
        text-align: left;
        box-shadow: 0 2px 8px rgba(236, 72, 153, 0.3);
    }
    .bot-message {
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        color: #000000;
        padding: 1rem 1.5rem;
        border-radius: 18px;
        margin: 0.8rem 0;
        max-width: 85%;
        border-left: 4px solid #ec4899;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .message-time {
        font-size: 0.7rem;
        opacity: 0.7;
        margin-top: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📝 Selfloom - Journaling & AI Assistant</div>', unsafe_allow_html=True)


# Sidebar

with st.sidebar:
    st.header("👤 Profil Pengguna")
    user_id = st.number_input("User ID", min_value=1, value=1, step=1)
    
    st.markdown("---")
    st.header("📊 Statistik")
    try:
        total_entries = session.query(journal_entries).filter_by(user_id=user_id).count()
        st.metric("Total Jurnal", total_entries)
        
        if total_entries > 0:
            mood_counts = session.query(journal_entries.c.mood).filter_by(user_id=user_id).all()
            mood_dict = {}
            for mood in mood_counts:
                mood_text = mood[0] if mood[0] else "Netral"
                mood_dict[mood_text] = mood_dict.get(mood_text, 0) + 1
            
            st.write("**Distribusi Mood:**")
            for mood, count in mood_dict.items():
                st.write(f"- {mood}: {count}")
    except Exception as e:
        st.error("Gagal memuat statistik")

# Tab Navigation

tab1, tab2, tab3 = st.tabs(["📓 Journaling", "🤖 AI Assistant", "📖 Riwayat Jurnal"])

with tab1:
    st.subheader("📓 Tulis Jurnal Hari Ini")
    
    with st.form("journal_form", clear_on_submit=True):
        journal_content = st.text_area(
            "Apa yang ingin Anda ceritakan hari ini?",
            placeholder="Tuliskan perasaan, pikiran, atau pengalaman Anda di sini...",
            height=150
        )
        
        submitted = st.form_submit_button("💾 Simpan Jurnal", use_container_width=True)
        
        if submitted:
            if not journal_content or len(journal_content.strip()) < 5:
                st.warning("⚠️ Mohon tulis jurnal minimal 5 karakter")
            else:
                success = add_journal_entry(user_id, journal_content.strip())
                if success:
                    st.rerun()

with tab2:
    st.subheader("🤖 Selfloom AI Assistant")
    st.markdown("**Chat dengan AI yang pintar dan empatik - seperti konsultan pribadi Anda!**")
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Chat container
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Display chat history
    if not st.session_state.chat_history:
        st.markdown("""
        <div class="bot-message">
            <strong>🤖 Selfloom AI:</strong><br><br>
            Halo! Saya Selfloom AI - asisten AI Anda yang pintar dan empatik. ✨<br><br>
            
            Saya bisa membantu Anda dengan:
            • 🧠Konseling & Dukungan Emosional- Ceritakan perasaan Anda
            • 📝Expert Journaling- Tips menulis jurnal yang efektif
            • 💡Problem Solving- Analisis masalah dan solusi
            • 🎯Goal Setting- Bantu tentukan tujuan hidup
            • 🌱Personal Growth- Pengembangan diri
            • 🔍Analisis Mendalam- Eksplorasi berbagai perspektif
            
            Apa yang ingin Anda diskusikan hari ini? Silakan tanyakan apa saja! 😊
        </div>
        """, unsafe_allow_html=True)
    else:
        for message in st.session_state.chat_history:
            if message['role'] == 'user':
                st.markdown(
                    f'<div class="user-message">'
                    f'<strong>👤 Anda:</strong><br>{message["content"]}'
                    f'<div class="message-time">{message.get("time", "")}</div>'
                    f'</div>', 
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="bot-message">'
                    f'<strong>🤖 Selfloom AI:</strong><br>{message["content"]}'
                    f'<div class="message-time">{message.get("time", "")}</div>'
                    f'</div>', 
                    unsafe_allow_html=True
                )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "Ketik pertanyaan atau cerita Anda...", 
            placeholder="Contoh: Saya merasa stres dengan deadline, bantu saya...",
            key="chat_input"
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            send_message = st.form_submit_button("🚀 Kirim Pesan", use_container_width=True)
        with col2:
            clear_chat = st.form_submit_button("🗑️ Hapus Chat", use_container_width=True)
        
        if clear_chat:
            st.session_state.chat_history = []
            st.rerun()
        
        if send_message and user_input.strip():
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M")
            
            # Add user message to chat history
            st.session_state.chat_history.append({
                "role": "user", 
                "content": user_input,
                "time": current_time
            })
            
            # Get AI response
            with st.spinner("🤔 AI sedang menganalisis dan menulis respons..."):
                ai_response = chat_with_gemini(user_input, st.session_state.chat_history)
            
            # Add AI response to chat history
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": ai_response,
                "time": current_time
            })
            
            st.rerun()

with tab3:
    st.subheader("📖 Riwayat Jurnal Terbaru")
    
    try:
        entries = session.query(journal_entries).filter_by(user_id=user_id)\
        .order_by(journal_entries.c.entry_date.desc()).limit(10).all()
        
        if entries:
            for entry in entries:
                mood_mapping = {
                    "Bahagia": "Bahagia", "Sedih": "Sedih", "Marah": "Marah",
                    "Cemas": "Cemas", "Netral": "Netral", "Banagra": "Bahagia",
                    "Narral": "Netral"
                }
                
                normalized_mood = mood_mapping.get(entry.mood, "Netral")
                mood_class = f"mood-{normalized_mood.lower()}"
                
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(f"""
                        <div class="journal-entry {mood_class}">
                            <h4>📅 {entry.entry_date} - Mood: <strong>{normalized_mood}</strong></h4>
                            <p>{entry.content}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        if st.button("🗑️ Hapus", key=f"delete_{entry.id}", type="secondary"):
                            if delete_journal_entry(entry.id):
                                st.success(" Jurnal berhasil dihapus!")
                                st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("Belum ada jurnal yang dicatat. Mulai menulis di tab Journaling!")
            
    except Exception as e:
        st.error(f"Gagal memuat riwayat jurnal: {e}")

# Footer & Cleanup

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "Selfloom &copy; 2024 - Journaling & AI Assistant untuk kesehatan mental"
    "</div>", 
    unsafe_allow_html=True
)

def cleanup():
    try:
        session.close()
    except:
        pass

import atexit
atexit.register(cleanup)
