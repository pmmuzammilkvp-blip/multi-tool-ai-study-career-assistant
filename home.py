import os
import re
import streamlit as st

from ui import inject_theme, hero, chips, card, stat_tile

st.set_page_config(page_title="AI Tools Dashboard", page_icon="🤖", layout="wide")
inject_theme()

hero("Ready to Create Something New?", "A suite of AI-powered tools built with RAG, Agents and LLMs")
chips(["Python", "Streamlit", "Groq", "Whisper", "ChromaDB", "Sentence-Transformers", "Tavily", "gTTS"])

PAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")

# card title -> page name (lowercase, no spaces/underscores/number prefix)
PAGE_KEYS = {
    "Study Pack": "studypack",
    "Study Assistant": "studyassistant",
    "Voice Mode": "voicemode",
    "Code Bot": "codebot",
    "Quiz Generator": "quizgenerator",
    "PPT Generator": "pptgenerator",
    "Audio Explainer": "audioexplainer",
    "Mind Map Generator": "mindmapgenerator",
    "Resume Analyzer": "resumeanalyzer",
    "AI Code Debugger": "aicodedebugger",
    "Mock Interview": "mockinterview",
    "Progress Dashboard": "progressdashbord",
    "Agent Activity": "agentactivity",
}


def find_page(key):
    """Find the real file in pages/ ignoring case, spaces, underscores and number prefixes.
    Returns None if it does not exist, so Home never crashes."""
    if not key or not os.path.isdir(PAGES_DIR):
        return None
    for f in sorted(os.listdir(PAGES_DIR)):
        if not f.endswith(".py"):
            continue
        name = re.sub(r"^\d+[_\-\s]*", "", f[:-3]).replace("_", "").replace(" ", "").lower()
        if name == key:
            return f"pages/{f}"
    return None


features = [
    ("🎁", "Study Pack", "One click builds a summary, mind map, flashcards, quiz and audio from your topic or documents."),
    ("📚", "Study Assistant", "Upload documents and ask questions. An AI agent decides whether to search your files or the live web."),
    ("🎙️", "Voice Mode", "Talk to the agent instead of typing. Speak in Tamil or English and hear the answer spoken back."),
    ("💻", "Code Bot", "Generates, explains and debugs code in any language, with a Continue button for long programs."),
    ("📝", "Quiz Generator", "Turns your documents into an interactive quiz with instant feedback, a final score and weak-topic practice."),
    ("🎞️", "PPT Generator", "Type a topic, get a styled, ready-to-present slide deck as a downloadable file."),
    ("🎧", "Audio Explainer", "Type or speak a topic and listen to a spoken explanation in Tamil or English."),
    ("🧠", "Mind Map Generator", "Turns any topic into a visual, branching concept map."),
    ("📄", "Resume Analyzer", "Matches your resume against a job description with a score and suggestions."),
    ("🐛", "AI Code Debugger", "Explains a bug, fixes the code and runs it to verify the fix works."),
    ("🗣️", "Mock Interview", "A multi-round interview from your resume. Answer by voice or text and get a score with feedback."),
    ("📊", "Progress Dashboard", "Track quiz scores, interview scores and your weak topics over time with charts."),
    ("🧭", "Agent Activity", "See which tool the agent used for each question: document search, web search or a direct reply."),
]

# stats
c1, c2, c3, c4 = st.columns(4)
for col, (n, l) in zip((c1, c2, c3, c4), [(len(features), "AI TOOLS BUILT"), ("4", "FILE FORMATS"), ("2", "AGENT TOOLS"), ("Hard", "LEETCODE SOLVED")]):
    col.markdown(stat_tile(n, l), unsafe_allow_html=True)
st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)

# feature cards
cols = st.columns(3)
for i, (icon, title, desc) in enumerate(features):
    with cols[i % 3]:
        st.markdown(card(title, desc, icon), unsafe_allow_html=True)
        page = find_page(PAGE_KEYS.get(title, ""))
        if page:
            st.page_link(page, label=f"Open {title} →", use_container_width=True)
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)