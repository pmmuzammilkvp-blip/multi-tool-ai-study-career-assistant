import streamlit as st
import os
from ingest import ingest_file
from rag_query import query_rag
import uuid
from shared import save_chat, list_chats, load_chat, delete_chat, voice_or_text

st.set_page_config(page_title="Study Assistant", page_icon="📚", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2.5rem; max-width: 900px; }
    [data-testid="stChatMessage"] {
        border-radius: 18px; padding: 18px 22px; margin-bottom: 18px;
        border: 1px solid #2E2E2C; animation: fadeIn 0.3s ease-in;
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(8px);} to { opacity: 1; transform: translateY(0);} }
    [data-testid="stChatInput"] textarea { border-radius: 14px; font-size: 15px; }
    .stButton button {
        border-radius: 10px; border: 1px solid #D97757; font-weight: 600;
        padding: 6px 18px; transition: all 0.2s ease;
    }
    .stButton button:hover { background-color: #D97757; border-color: #D97757; transform: scale(1.02); }
    [data-testid="stSidebar"] { background-color: #171716; }
    [data-testid="stSidebarNav"] a { border-radius: 8px; margin: 3px 8px; padding: 8px 10px; font-size: 14.5px; }
    [data-testid="stSidebarNav"] a:hover { background-color: #2A2A28; }
    [data-testid="stSidebarNav"] a[aria-current="page"] { background-color: #2E2420; border-left: 3px solid #D97757; }
    h1 { letter-spacing: -0.5px; }
    .tool-badge {
        display: inline-block; background: rgba(217, 119, 87, 0.15); color: #D97757;
        font-size: 11.5px; font-weight: 600; padding: 3px 10px; border-radius: 12px; margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📚 Study Assistant")
st.caption("Ask questions about your uploaded documents")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())

with st.sidebar:
    st.header("💾 Saved Chats")
    if st.button("🆕 New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_id = str(uuid.uuid4())
        st.rerun()

    saved = list_chats("study_assistant")
    if not saved:
        st.caption("No saved chats yet")
    for cid, title, ts in saved:
        col1, col2 = st.columns([5, 1])
        with col1:
            if st.button(f"💬 {title}", key=f"load_{cid}", use_container_width=True):
                st.session_state.messages = load_chat("study_assistant", cid)
                st.session_state.chat_id = cid
                st.rerun()
            st.caption(ts)
        with col2:
            if st.button("🗑️", key=f"del_{cid}"):
                delete_chat("study_assistant", cid)
                st.rerun()

    st.markdown("---")
    st.header("📁 Upload Documents")
    uploaded_files = st.file_uploader(
        "PDF, PPTX, DOCX, TXT upload",
        type=["pdf", "pptx", "docx", "txt"],
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("Process Files"):
            os.makedirs("data", exist_ok=True)
            for file in uploaded_files:
                file_path = os.path.join("data", file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                with st.spinner(f"Processing {file.name}..."):
                    num_chunks = ingest_file(file_path, file.name)
                st.success(f"✅ {file.name}: {num_chunks} chunks added")

# Mic + typed input (mic stays at the top so the chat layout doesn't jump around)
prompt = voice_or_text("Ask your question...", key="study", is_chat=True)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("tool"):
            st.markdown(f"<span class='tool-badge'>🔧 {message['tool']}</span>", unsafe_allow_html=True)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer, tool_used = query_rag(prompt)
            st.markdown(answer)
            st.markdown(f"<span class='tool-badge'>🔧 {tool_used}</span>", unsafe_allow_html=True)

    st.session_state.messages.append({"role": "assistant", "content": answer, "tool": tool_used})
    save_chat("study_assistant", st.session_state.chat_id, st.session_state.messages)