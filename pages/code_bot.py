import streamlit as st
from groq import Groq
import os
from dotenv import load_dotenv
from shared import voice_or_text
import re

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

SYSTEM_PROMPT = (
    "You are an expert coding assistant. Write clean, well-commented code. "
    "Always answer in the programming language of the user's code or the language they ask for. "
    "Use Python only when no language is mentioned. Never switch to a different language on your own. "
    "Explain your solution briefly after the code block. "
    "You can see the earlier conversation. When the user says things like "
    "'explain that code', 'this code', 'fix it', or 'make it faster', "
    "they mean the code from the earlier messages. Explain, debug or modify "
    "that code in detail instead of asking them to paste it again."
)

# How many past messages to send to the model (limit / token save)
HISTORY_LIMIT = 16

if "code_messages" not in st.session_state:
    st.session_state.code_messages = []

# Clear chat button
if st.session_state.code_messages:
    if st.button("🗑️ Clear chat"):
        st.session_state.code_messages = []
        st.rerun()

CONTINUE_SYSTEM = (
    "You continue an answer that was cut off by a length limit. "
    "Output ONLY the raw text that comes immediately after the given ending. "
    "Never repeat any earlier text, never restart from the beginning, never add an "
    "introduction, explanation, apology or comment, and never open a new code fence."
)


def call_groq(history, system=None, temperature=None):
    messages = [{"role": "system", "content": system or SYSTEM_PROMPT}] + [
        {"role": m["role"], "content": m["content"]} for m in history
    ]
    kwargs = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    response = groq_client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=messages,
        max_tokens=900,
        **kwargs
    )
    choice = response.choices[0]
    return choice.message.content or "", choice.finish_reason


def looks_cut(text, finish_reason):
    # token limit ku cut aachu, illana code block open aagi close aagala
    return finish_reason == "length" or text.count("```") % 2 == 1


def clean_continuation(existing, new):
    """Continue part la irundhu extra fence, repeat aana text ellam remove pannum."""
    # 1. Code block ulla irukkumbodhu pudhu opening fence vandha remove
    if existing.count("```") % 2 == 1:
        new = re.sub(r"^\s*```[a-zA-Z0-9_+\-]*[ \t]*\n", "", new, count=1)

    # 2. Previous ending oda overlap irundha remove
    max_k = min(len(existing), len(new), 600)
    for k in range(max_k, 14, -1):
        if existing.endswith(new[:k]):
            return new[k:]

    # 3. Model konjam munnaadi irundhu repeat pannirundha, repeat aana part ah remove
    probe = new[:80]
    if len(probe) >= 30:
        idx = existing.rfind(probe)
        if idx != -1:
            overlap = len(existing) - idx
            if existing[idx:] == new[:overlap]:
                return new[overlap:]
    return new


def continue_last_answer(msgs):
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
    # model fence close pannama nindrutha, nammale close pannidalaam
    if reason != "length" and merged.count("```") % 2 == 1:
        merged += "\n```"
    return merged, reason


msgs = st.session_state.code_messages

# Mic + typed input (mic stays at the top so the chat layout doesn't jump around)
prompt = voice_or_text("Ask me to write, explain, or debug code...", key="codebot", is_chat=True)

# 1. Pudhu prompt vandha, mudhal answer generate pannunga
if prompt:
    if msgs:
        msgs[-1]["cut"] = False  # pazhaya warning remove
    msgs.append({"role": "user", "content": prompt})
    with st.spinner("Thinking..."):
        try:
            text, reason = call_groq(msgs[-HISTORY_LIMIT:])
            msgs.append({"role": "assistant", "content": text, "cut": looks_cut(text, reason)})
        except Exception as e:
            msgs.append({"role": "assistant", "content": f"⚠️ Error: {e}", "cut": False})

# 2. Chat history kaattunga (last message cut aana warning)
for i, m in enumerate(msgs):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("cut") and i == len(msgs) - 1:
            st.warning("⚠️ CThe Abouve code is incomplete because of rate limit so click the continue button to get the remaining code")

# 3. Last message cut aana Continue button
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