import streamlit as st
from groq import Groq
from gtts import gTTS
import io
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Audio Explainer", page_icon="🎧", layout="wide")

st.markdown("""
<style>
    .block-container {
        padding-top: 2.5rem;
        max-width: 900px;
    }
    [data-testid="stChatMessage"] {
        border-radius: 18px;
        padding: 18px 22px;
        margin-bottom: 18px;
        border: 1px solid #2E2E2C;
    }
    .stButton button {
        border-radius: 10px;
        border: 1px solid #D97757;
        font-weight: 600;
        padding: 6px 18px;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        background-color: #D97757;
        border-color: #D97757;
        transform: scale(1.02);
    }
    [data-testid="stSidebar"] {
        background-color: #171716;
    }
    [data-testid="stSidebarNav"] a {
        border-radius: 8px;
        margin: 3px 8px;
        padding: 8px 10px;
        font-size: 14.5px;
    }
    [data-testid="stSidebarNav"] a:hover {
        background-color: #2A2A28;
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background-color: #2E2420;
        border-left: 3px solid #D97757;
    }
    h1 {
        letter-spacing: -0.5px;
    }
    [data-testid="stAlertContainer"] {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎧 Audio Explainer")
st.caption("Type a topic and listen to a spoken explanation")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

LANG_CODES = {"English": "en", "Tamil": "ta"}
# Tamil limit raised a bit because audio is now generated in parallel chunks
WORD_LIMITS = {"English": 200, "Tamil": 150}

# Extra rule per language for the LLM prompt
LANG_RULES = {
    "English": "",
    "Tamil": (
        "- Write ONLY in Tamil script (தமிழ்). Do not use English letters or transliteration. "
        "Write English technical terms in Tamil script the way they sound (for example RAG as ஆர்ஏஜி)."
    ),
}


def split_chunks(text, max_len=200):
    """Split script into sentence-based chunks so TTS can run in parallel."""
    sentences = re.split(r"(?<=[.!?।])\s+", text)
    chunks, cur = [], ""
    for s in sentences:
        if len(cur) + len(s) > max_len and cur:
            chunks.append(cur.strip())
            cur = ""
        cur += s + " "
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


def tts_chunk(text, lang_code, slow):
    buf = io.BytesIO()
    gTTS(text=text, lang=lang_code, slow=slow).write_to_fp(buf)
    return buf.getvalue()


def clean_script(text):
    # remove model "thinking" blocks so they are never read aloud
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


topic = st.text_input("Topic to explain (e.g. 'RAG concept for my seminar'):")
col1, col2 = st.columns([2, 1])
with col1:
    language = st.selectbox("Audio language", ["English", "Tamil"])
with col2:
    slow = st.checkbox("Slow speech", value=False)

if st.button("Generate Audio"):
    if not topic:
        st.warning("Please enter a topic first.")
    else:
        try:
            with st.spinner("Writing the explanation..."):
                prompt = f"""Explain "{topic}" as a spoken explanation in {language}.
Rules:
- Write like a teacher talking to a student, in natural spoken language.
- No markdown, no bullet points, no headings, no symbols, no emojis, no code.
- Use short, simple sentences.
- Maximum {WORD_LIMITS[language]} words.
- Start with a one-line hook, explain with a simple real-life analogy, and end with a one-line summary.
{LANG_RULES[language]}"""

                response = groq_client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=[
                        {"role": "system", "content": "You are a friendly teacher who explains topics in clear spoken language."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=900,
                )
                script = clean_script(response.choices[0].message.content)

            chunks = split_chunks(script)
            parts = [None] * len(chunks)
            progress = st.progress(0, text="Converting to audio...")

            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {
                    pool.submit(tts_chunk, c, LANG_CODES[language], slow): idx
                    for idx, c in enumerate(chunks)
                }
                for done, fut in enumerate(as_completed(futures), 1):
                    parts[futures[fut]] = fut.result()  # keeps original order
                    progress.progress(done / len(chunks), text="Converting to audio...")
            progress.empty()

            st.session_state.audio_bytes = b"".join(parts)
            st.session_state.audio_script = script
            st.session_state.audio_topic = topic
        except Exception as e:
            st.error(f"Something went wrong: {e}")

if "audio_bytes" in st.session_state:
    st.success("✅ Audio ready!")
    st.audio(st.session_state.audio_bytes, format="audio/mp3")
    st.download_button(
        "📥 Download MP3",
        data=st.session_state.audio_bytes,
        file_name=f"{st.session_state.audio_topic.replace(' ', '_')}.mp3",
        mime="audio/mpeg",
    )
    with st.expander("📄 Read the script"):
        st.write(st.session_state.audio_script)