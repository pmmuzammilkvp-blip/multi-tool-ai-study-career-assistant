import streamlit as st
from groq import Groq
from gtts import gTTS
import io
import os
import re
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from rag_query import query_rag

load_dotenv()

st.set_page_config(page_title="Voice Mode", page_icon="🎙️", layout="wide")

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
        animation: fadeIn 0.3s ease-in;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
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
    .tool-badge {
        display: inline-block; background: rgba(217, 119, 87, 0.15); color: #D97757;
        font-size: 11.5px; font-weight: 600; padding: 3px 10px; border-radius: 12px; margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎙️ Voice Mode")
st.caption("Talk to the agent instead of typing: speak your question, hear the answer")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CHAT_MODEL = "qwen/qwen3.8-27b"
STT_MODEL = "whisper-large-v3"

LANG_CODES = {"English": "en", "Tamil": "ta"}
WORD_LIMITS = {"English": 120, "Tamil": 100}
LANG_RULES = {
    "English": "",
    "Tamil": (
        "- Write ONLY in Tamil script (தமிழ்). Do not use English letters or transliteration. "
        "Write English technical terms in Tamil script the way they sound."
    ),
}

st.session_state.setdefault("voice_chat", [])      # list of {"q","a","spoken","tool","audio"}
st.session_state.setdefault("voice_last_hash", None)


# ---------------- helpers ----------------
def clean(text):
    # removes finished and unfinished <think> blocks
    return re.sub(r"<think>.*?(</think>|$)", "", text, flags=re.DOTALL).strip()


def transcribe(audio_bytes, lang_code):
    result = groq_client.audio.transcriptions.create(
        file=("voice.wav", audio_bytes),
        model=STT_MODEL,
        language=lang_code,
        response_format="json",
    )
    return result.text.strip()


def to_spoken(answer, language):
    """Turn the agent's written answer into short spoken language (no markdown, right language)."""
    resp = groq_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You turn written answers into natural spoken explanations for a student."},
            {"role": "user", "content": f"""Rewrite this answer as a spoken explanation in {language}.

Answer:
{answer}

Rules:
- Keep the meaning and the important facts. Do not add new facts.
- No markdown, no bullet points, no headings, no symbols, no emojis, no code.
- Short, simple sentences, like a teacher talking to a student.
- Maximum {WORD_LIMITS[language]} words.
{LANG_RULES[language]}"""},
        ],
        max_tokens=1200,
    )
    return clean(resp.choices[0].message.content)


def split_chunks(text, max_len=200):
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


def tts_chunk(text, lang_code):
    buf = io.BytesIO()
    gTTS(text=text, lang=lang_code).write_to_fp(buf)
    return buf.getvalue()


def speak(text, lang_code):
    chunks = split_chunks(text)
    parts = [None] * len(chunks)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(tts_chunk, c, lang_code): i for i, c in enumerate(chunks)}
        for fut in as_completed(futures):
            parts[futures[fut]] = fut.result()
    return b"".join(parts)


# ---------------- UI ----------------
top1, top2 = st.columns([2, 1])
with top1:
    language = st.selectbox("Speaking & answer language", ["English", "Tamil"])
with top2:
    st.write("")
    st.write("")
    if st.button("🗑️ Clear conversation"):
        st.session_state.voice_chat = []
        st.session_state.voice_last_hash = None
        st.rerun()

lang_code = LANG_CODES[language]

audio = st.audio_input("🎙️ Click the mic, speak your question, then click stop")

if audio is not None:
    audio_bytes = audio.getvalue()
    audio_hash = hashlib.md5(audio_bytes).hexdigest()

    # process each recording only once (Streamlit reruns the script a lot)
    if audio_hash != st.session_state.voice_last_hash:
        st.session_state.voice_last_hash = audio_hash
        try:
            with st.spinner("🎧 Listening..."):
                question = transcribe(audio_bytes, lang_code)

            if not question:
                st.warning("I couldn't hear anything. Please try again, closer to the mic.")
            else:
                with st.spinner("🤔 Thinking..."):
                    # same agent as the Study Assistant: document search / web search / direct reply
                    history = []
                    for t in st.session_state.voice_chat[-4:]:
                        history += [
                            {"role": "user", "content": t["q"]},
                            {"role": "assistant", "content": t["a"]},
                        ]
                    answer, tool_used = query_rag(question, history=history)
                with st.spinner("🔊 Preparing voice..."):
                    spoken = to_spoken(answer, language)
                    voice = speak(spoken, lang_code)
                st.session_state.voice_chat.append(
                    {"q": question, "a": answer, "spoken": spoken, "tool": tool_used, "audio": voice}
                )
        except Exception as e:
            st.error(f"Something went wrong: {e}")

# show conversation, newest at the bottom
for turn in st.session_state.voice_chat:
    with st.chat_message("user"):
        st.write(turn["q"])
    with st.chat_message("assistant"):
        st.markdown(turn["a"])
        st.markdown(f"<span class='tool-badge'>🔧 {turn['tool']}</span>", unsafe_allow_html=True)
        st.audio(turn["audio"], format="audio/mp3")
        with st.expander("🗣️ Spoken script"):
            st.write(turn["spoken"])

if not st.session_state.voice_chat:
    st.info("Tip: ask about your uploaded notes, or something current like today's news, and watch the 🔧 badge.")