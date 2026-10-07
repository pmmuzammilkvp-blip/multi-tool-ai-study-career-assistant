import streamlit as st
from groq import Groq
import os
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

CONTINUE_PROMPT = (
    "Continue the code exactly from where it stopped. "
    "Put it in a new code block and do not repeat earlier code."
)

if "code_truncated" not in st.session_state:
    st.session_state.code_truncated = False

# Mic + typed input (mic stays at the top so the chat layout doesn't jump around)
prompt = voice_or_text("Ask me to write, explain, or debug code...", key="codebot", is_chat=True)

for message in st.session_state.code_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Pazhaya response cut aagi irundha: warning + continue button
if st.session_state.code_truncated and not prompt:
    st.warning("⚠️ There is only half code is generated because of the token limit so plese click the continue button to get the remaining code.")
    if st.button("➡️ Continue generating", key="continue_btn"):
        prompt = CONTINUE_PROMPT

if prompt:
    st.session_state.code_truncated = False
    st.session_state.code_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # System prompt + recent chat history (includes the new prompt)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages += st.session_state.code_messages[-HISTORY_LIMIT:]

            truncated = False
            try:
                response = groq_client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=messages,
                    max_tokens=900
                )
                choice = response.choices[0]
                answer = choice.message.content or ""

                truncated = (choice.finish_reason == "length")
            except Exception as e:
                answer = f"⚠️ Error: {e}"
            st.markdown(answer)

    st.session_state.code_messages.append({"role": "assistant", "content": answer})
    st.session_state.code_truncated = truncated
    if truncated:
        st.rerun()