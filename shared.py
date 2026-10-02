import chromadb
from sentence_transformers import SentenceTransformer
import json
import hashlib
import streamlit as st
from groq import Groq
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

model = SentenceTransformer('all-MiniLM-L6-v2')
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="study_docs")


def search_knowledge_base(query, n_results=3):
    query_embedding = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results
    )
    return results['documents'][0], results['metadatas'][0]


# ---------------- Chat history ----------------
HISTORY_FILE = "data/chat_history.json"


def _load_all_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save_all_history(data):
    os.makedirs("data", exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_chat(page_key, chat_id, messages):
    if not messages:
        return
    all_data = _load_all_history()
    page_chats = all_data.get(page_key, {})
    title = messages[0]["content"][:40] + ("..." if len(messages[0]["content"]) > 40 else "")
    page_chats[chat_id] = {
        "title": title,
        "timestamp": datetime.now().strftime("%d %b, %I:%M %p"),
        "messages": messages,
    }
    all_data[page_key] = page_chats
    _save_all_history(all_data)


def list_chats(page_key):
    all_data = _load_all_history()
    page_chats = all_data.get(page_key, {})
    items = [(cid, c["title"], c["timestamp"]) for cid, c in page_chats.items()]
    return sorted(items, key=lambda x: x[0], reverse=True)


def load_chat(page_key, chat_id):
    all_data = _load_all_history()
    return all_data.get(page_key, {}).get(chat_id, {}).get("messages", [])


def delete_chat(page_key, chat_id):
    all_data = _load_all_history()
    if page_key in all_data and chat_id in all_data[page_key]:
        del all_data[page_key][chat_id]
        _save_all_history(all_data)


# ---------------- Agent activity tracking ----------------
STATS_FILE = "data/agent_stats.json"
DEFAULT_COUNTS = {"Document Search": 0, "Web Search": 0, "Direct Reply": 0}


def _load_stats():
    if not os.path.exists(STATS_FILE):
        return {"counts": dict(DEFAULT_COUNTS), "log": []}
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            for k in DEFAULT_COUNTS:
                data.setdefault("counts", {}).setdefault(k, 0)
            return data
        except json.JSONDecodeError:
            return {"counts": dict(DEFAULT_COUNTS), "log": []}


def _save_stats(data):
    os.makedirs("data", exist_ok=True)
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def log_tool_use(tool_label, question):
    data = _load_stats()
    data["counts"][tool_label] = data["counts"].get(tool_label, 0) + 1
    data["log"].insert(0, {
        "tool": tool_label,
        "question": question[:80],
        "timestamp": datetime.now().strftime("%d %b, %I:%M %p"),
    })
    data["log"] = data["log"][:20]
    _save_stats(data)


def get_agent_stats():
    return _load_stats()


# ---------------- Voice input (mic + text) ----------------
def voice_or_text(label, key, placeholder="", is_chat=False, height=None, language=None):
    """
    Mic + text input together.

    - is_chat=True  -> returns the prompt ONCE (typed, or the new voice recording)
    - is_chat=False -> the spoken text is written into the text box so the user
                       can edit it and then press the page's own button as usual
    - language: "en" / "ta" / None (None = Whisper auto-detects)
    - `key` must be unique on every page, e.g. "quiz", "debugger", "resume"
    """
    audio_value = st.audio_input("🎤 Or speak", key=f"{key}_audio")
    voice_text = None

    if audio_value is not None:
        audio_bytes = audio_value.getvalue()
        audio_hash = hashlib.md5(audio_bytes).hexdigest()
        done_key = f"{key}_last_audio"

        # transcribe each recording only once (Streamlit reruns the page on every click)
        if st.session_state.get(done_key) != audio_hash:
            st.session_state[done_key] = audio_hash
            with st.spinner("Transcribing..."):
                transcribe_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                kwargs = {"language": language} if language else {}
                transcript = transcribe_client.audio.transcriptions.create(
                    file=("input.wav", audio_bytes),
                    model="whisper-large-v3",
                    **kwargs,
                )
            voice_text = transcript.text.strip()
            if voice_text:
                st.info(f"🎤 Heard: \"{voice_text}\"")

    if is_chat:
        typed = st.chat_input(label)
        return typed or voice_text

    # text_input / text_area: put the spoken words inside the box
    # (must be set BEFORE the widget is created below)
    if voice_text:
        st.session_state[f"{key}_text"] = voice_text

    if height:
        typed = st.text_area(label, placeholder=placeholder, height=height, key=f"{key}_text")
    else:
        typed = st.text_input(label, placeholder=placeholder, key=f"{key}_text")
    return typed


# ---------------- Progress tracking (quiz + mock interview) ----------------
PROGRESS_FILE = "data/progress.json"


def _demo_mode():
    # In the public deployment (DEMO_MODE=1) progress is kept per visitor in session_state,
    # so people never see each other's scores. Locally it is saved in a file.
    return os.getenv("DEMO_MODE") == "1"


def _load_progress_file():
    if not os.path.exists(PROGRESS_FILE):
        return []
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def log_progress(kind, score, total, topic="", weak=None):
    """kind: 'quiz' or 'interview'. For interviews score/total are summed points."""
    entry = {
        "kind": kind,
        "score": score,
        "total": total,
        "pct": round(100 * score / total) if total else 0,
        "topic": topic,
        "weak": list(weak or []),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    if _demo_mode():
        st.session_state.setdefault("progress_log", []).append(entry)
        return
    entries = _load_progress_file()
    entries.append(entry)
    os.makedirs("data", exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def get_progress():
    if _demo_mode():
        return list(st.session_state.get("progress_log", []))
    return _load_progress_file()


def clear_progress():
    if _demo_mode():
        st.session_state["progress_log"] = []
    elif os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)