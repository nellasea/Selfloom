# selfloom_app.py
import os
from dotenv import load_dotenv
import streamlit as st
import google.generativeai as genai
import datetime
import json

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.error("API key tidak ditemukan. Tambahkan GOOGLE_API_KEY di file .env")
    st.stop()

# Konfigurasi Gemini (SDK versi bisa berbeda; cek docs)
genai.configure(api_key=API_KEY)

st.set_page_config(page_title="Selfloom", page_icon="🧵", layout="centered")
st.title("🧵 Selfloom — A Gentle AI Companion")
st.caption("Curhat di sini. Selfloom akan mendengarkan dan memberikan saran yang lembut.")

# Inisialisasi session state
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role":"user"/"assistant", "text": "..."}
if "mood" not in st.session_state:
    st.session_state.mood = None

# Helper: simpan chat ke file
def save_chat_to_file(chat_list, filename=None):
    if not filename:
        t = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"saved_chats/chat_{t}.json"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(chat_list, f, ensure_ascii=False, indent=2)
    return filename

# Simple mood detection using Gemini: returns label kecil
def detect_mood_with_gemini(text):
    # Prompt ringkas: model diminta beri label mood singkat
    system_prompt = (
        "You are a concise sentiment classifier. "
        "Given the user's message, respond with a single word mood label from: "
        "happy, calm, neutral, sad, anxious, angry, hopeless. "
        "Only output the single word label in lowercase."
    )
    # Panggil model (sesuaikan API/SDK jika berbeda)
    resp = genai.responses.create(
        model="gemini flash 2.5",  # contoh nama; ganti sesuai akun/akses Gemini
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        temperature=0.0,
        max_output_tokens=10,
    )
    # Ambil text output. Struktur respons bisa berubah per SDK versi.
    label = None
    try:
        # beberapa SDK punya output_text langsung
        label = resp.output_text.strip().splitlines()[0].strip().lower()
    except Exception:
        # fallback: coba parse output[0]
        try:
            label = resp.output[0].content[0].text.strip().lower()
        except Exception:
            label = "neutral"
    # safety: sanitasi
    allowed = {"happy","calm","neutral","sad","anxious","angry","hopeless"}
    if label not in allowed:
        return "neutral"
    return label

# Function untuk minta saran/empathetic reply ke Gemini
def ask_selfloom(user_text, mood_hint=None):
    persona = (
        "You are Selfloom, a gentle empathetic AI companion. "
        "Respond with warmth, short practical suggestions, and avoid clinical/medical advice. "
        "If the user expresses hopelessness or danger, respond with supportive words and advise them to seek professional/crisis help."
    )
    # Tambahkan mood jika ada
    prompt = f"{persona}\n\nUser message:\n{user_text}\n\n"
    if mood_hint:
        prompt += f"(Detected mood: {mood_hint})\n\n"
    prompt += (
        "Respond in Indonesian. "
        "First line: one-sentence empathetic reflection. "
        "Second part: 3 short actionable suggestions (each on new line) "
        "Keep answer concise (max 180 words)."
    )

    resp = genai.responses.create(
        model="gemini flash 2.5",  # ganti sesuai akses
        messages=[
            {"role":"system", "content": persona},
            {"role":"user", "content": prompt}
        ],
        temperature=0.4,
        max_output_tokens=300,
    )
    try:
        answer = resp.output_text
    except Exception:
        try:
            answer = resp.output[0].content[0].text
        except Exception:
            answer = "Maaf, terjadi kesalahan memproses jawaban."
    return answer.strip()

# UI: input area
with st.form(key="chat_form", clear_on_submit=False):
    user_input = st.text_area("Tulis curhatanmu di sini...", height=140, placeholder="Ceritakan apa yang kamu rasakan...")
    submitted = st.form_submit_button("Kirim")

# Tombol helper
col1, col2, col3 = st.columns([1,1,1])
with col1:
    if st.button("Refleksi singkat"):
        # Generate a short reflection prompt
        st.session_state.messages.append({"role":"assistant", "text":"Coba ceritakan satu hal kecil yang membuatmu tersenyum hari ini."})
with col2:
    if st.button("Simpan percakapan"):
        if st.session_state.messages:
            fname = save_chat_to_file(st.session_state.messages)
            st.success(f"Percakapan disimpan: {fname}")
        else:
            st.info("Belum ada percakapan untuk disimpan.")
with col3:
    if st.button("Bersihkan percakapan"):
        st.session_state.messages = []
        st.session_state.mood = None
        st.info("Percakapan dibersihkan.")

# Proses pengiriman
if submitted and user_input.strip():
    # tampilkan user di history
    st.session_state.messages.append({"role":"user", "text": user_input.strip()})
    # mood detection (sederhana)
    mood = detect_mood_with_gemini(user_input.strip())
    st.session_state.mood = mood
    # buat reply dari Selfloom
    reply = ask_selfloom(user_input.strip(), mood_hint=mood)
    st.session_state.messages.append({"role":"assistant", "text": reply})

# Tampilkan mood dan history
if st.session_state.mood:
    st.markdown(f"**Mood terdeteksi:** `{st.session_state.mood}`")

st.markdown("---")
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"**Kamu:** {msg['text']}")
    else:
        st.markdown(f"**Selfloom:** {msg['text']}")

# Footer privacy note
st.markdown("---")
st.caption("Privacy note: Percakapan hanya disimpan jika kamu memilih 'Simpan percakapan'. Jangan menaruh info sensitif seperti nomor identitas atau data finansial.")
