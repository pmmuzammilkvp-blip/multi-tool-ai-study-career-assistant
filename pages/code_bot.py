import os
import re
import time
import streamlit as st
from groq import Groq, RateLimitError
from dotenv import load_dotenv
from shared import voice_or_text

load_dotenv()

st.set_page_config(page_title="Code Bot", page_icon="💻", layout="wide")

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
    [data-testid="stChatInput"] textarea {
        border-radius: 14px;
        font-size: 15px;
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
</style>
""", unsafe_allow_html=True)

st.title("💻 Code Bot")
st.caption("Ask me to write, explain, or debug code")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "qwen/qwen3.8-27b"
MAX_TOKENS = 900      # per request (Groq free tier: 1000 output tokens per minute)
MAX_PARTS = 4         # long code can be built from up to 4 parts
HISTORY_LIMIT = 16    # how many past messages are sent to the model

SYSTEM_PROMPT = (
    "You are an expert coding assistant. Write clean, well-commented code. "
    "Always answer in the programming language of the user's code or the language they ask for. "
    "Use Python only when no language is mentioned. Never switch to a different language on your own. "
    "Explain your solution briefly after the code block. "
    "You can see the earlier conversation. When the user says things like "
    "'explain that code', 'this code', 'fix it', or 'make it faster', "
    "they mean the code from the earlier messages. Explain, debug or modify "
    "that code in detail instead of asking them to paste it again. "
    "Write explanations in the same language the user writes in, "
    "but keep code, variable names and comments in English. "
    "Always put code inside a fenced code block with the language name, and never leave it unclosed. "
    "Write complete code, do not shorten it. "
    "When asked to explain code, explain it step by step in simple words without rewriting it."
)

CONTINUE_SYSTEM = (
    "You continue an answer that was cut off by a length limit. "
    "Output ONLY the raw text that comes immediately after the given ending. "
    "Never repeat any earlier text, never restart from the beginning, never add an "
    "introduction, explanation, apology or comment, and never open a new code fence."
)

CUT_WARNING = (
    "⚠️ The code was cut off by the response length limit and is incomplete. "
    "Click Continue to generate the rest."
)

if "code_messages" not in st.session_state:
    st.session_state.code_messages = []

# Clear chat button
if st.session_state.code_messages:
    if st.button("🗑️ Clear chat"):
        st.session_state.code_messages = []
        st.rerun()


# ---------------- helpers ----------------
def _retry_seconds(err):
    """Read 'try again in 28.38s' or '1m5.2s' from a Groq rate-limit error."""
    m = re.search(r"try again in (?:(\d+)m)?\s*([\d.]+)s", str(err))
    if not m:
        return 30.0
    return int(m.group(1) or 0) * 60 + float(m.group(2))


def call_groq(history, system=None, temperature=None):
    messages = [{"role": "system", "content": system or SYSTEM_PROMPT}] + [
        {"role": m["role"], "content": m["content"]} for m in history
    ]
    kwargs = {}
    if temperature is not None:
        kwargs["temperature"] = temperature

    for attempt in range(3):
        try:
            response = groq_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=MAX_TOKENS,
                **kwargs
            )
            choice = response.choices[0]
            return choice.message.content or "", choice.finish_reason
        except RateLimitError as e:
            wait = _retry_seconds(e) + 1
            if attempt == 2 or wait > 65:
                raise Exception(
                    "Groq free-tier rate limit reached (1000 output tokens per minute). "
                    "Please try again in a minute."
                )
            with st.spinner(f"Rate limit reached. Retrying automatically in {int(wait)} seconds..."):
                time.sleep(wait)


def looks_cut(text, finish_reason):
    # cut by the token limit, or a code block was opened but never closed
    return finish_reason == "length" or text.count("```") % 2 == 1


def clean_continuation(existing, new):
    """Remove extra fences and repeated text from a continuation."""
    # 1. If we are inside a code block, drop a new opening fence
    if existing.count("```") % 2 == 1:
        new = re.sub(r"^\s*```[a-zA-Z0-9_+\-]*[ \t]*\n", "", new, count=1)

    # 2. Remove overlap between the old ending and the new start
    max_k = min(len(existing), len(new), 600)
    for k in range(max_k, 14, -1):
        if existing.endswith(new[:k]):
            return new[k:]

    # 3. Model restarted from earlier text: drop the repeated part
    probe = new[:80]
    if len(probe) >= 30:
        idx = existing.rfind(probe)
        if idx != -1:
            overlap = len(existing) - idx
            if existing[idx:] == new[:overlap]:
                return new[overlap:]
    return new


def continue_last_answer(msgs):
    """Generate only the remaining part of the last (cut) answer."""
    partial = msgs[-1]["content"]
    last_user = next((m["content"] for m in reversed(msgs) if m["role"] == "user"), "")
    tail = partial[-400:]
    history = [
        {"role": "user", "content": last_user},
        {"role": "assistant", "content": partial},
        {"role": "user", "content": (
            "Your answer above was cut off. Its last characters are:\n<<<\n"
            f"{tail}\n>>>\n"
            "Write ONLY what comes right after that text, as a raw continuation. "
            "Do not repeat anything, no introduction, no new opening ``` fence. "
            "When the code is complete, close it with ``` and stop."
        )},
    ]
    text, reason = call_groq(history, system=CONTINUE_SYSTEM, temperature=0.2)
    merged = partial + clean_continuation(partial, text)
    # if the model stopped without closing the fence, close it
    if reason != "length" and merged.count("```") % 2 == 1:
        merged += "\n```"
    return merged, reason


def generate_full(history, status, box):
    """Short code finishes in one call. Long code is built from several parts automatically."""
    text, reason = call_groq(history)
    merged = text
    box.markdown(merged)
    part = 1
    while looks_cut(merged, reason) and part < MAX_PARTS:
        part += 1
        status.update(
            label=f"📦 Long code: generating part {part}/{MAX_PARTS} "
                  "(this may pause briefly because of rate limits)..."
        )
        try:
            merged, reason = continue_last_answer(
                history + [{"role": "assistant", "content": merged}]
            )
        except Exception:
            return merged, True  # keep what we have, show the Continue button
        box.markdown(merged)
    return merged, looks_cut(merged, reason)


# ---------------- UI ----------------
msgs = st.session_state.code_messages

# Mic + typed input (mic stays at the top so the chat layout doesn't jump around)
prompt = voice_or_text("Ask me to write, explain, or debug code...", key="codebot", is_chat=True)

# New prompt: remove the old warning
if prompt and msgs:
    msgs[-1]["cut"] = False

# 1. Show chat history (warning only on the last message if it was cut)
for i, m in enumerate(msgs):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("cut") and i == len(msgs) - 1:
            st.warning(CUT_WARNING)

# 2. New prompt: generate live
if prompt:
    msgs.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status = st.status("⚡ Generating...", expanded=False)
        box = st.empty()
        try:
            text, cut = generate_full(msgs[-HISTORY_LIMIT:], status, box)
            msgs.append({"role": "assistant", "content": text, "cut": cut})
            status.update(label="✅ Done" if not cut else "⚠️ Cut off", state="complete")
            if cut:
                st.warning(CUT_WARNING)
        except Exception as e:
            status.update(label="⚠️ Error", state="error")
            box.markdown(f"⚠️ {e}")
            msgs.append({"role": "assistant", "content": f"⚠️ {e}", "cut": False})

# 3. Continue button if the last answer is still incomplete
if msgs and msgs[-1].get("cut"):
    if st.button("➡️ Continue generating", key="continue_btn"):
        ok = True
        with st.spinner("Continuing..."):
            try:
                merged, reason = continue_last_answer(msgs)
                msgs[-1]["content"] = merged
                msgs[-1]["cut"] = looks_cut(merged, reason)
            except Exception as e:
                ok = False
                st.error(f"⚠️ {e}")
        if ok:
            st.rerun()