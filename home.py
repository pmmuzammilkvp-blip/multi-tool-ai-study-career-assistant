import os
import re
import streamlit as st

st.set_page_config(page_title="AI Tools Dashboard", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    .block-container {
        padding-top: 2.5rem;
        max-width: 1200px;
    }
    #MainMenu, footer {visibility: hidden;}

    /* Hero */
    .hero-badge {
        width: 78px; height: 78px; border-radius: 50%;
        background: linear-gradient(135deg, #D97757, #E8A87C);
        display: flex; align-items: center; justify-content: center;
        font-size: 34px; margin: 0 auto 18px auto;
        box-shadow: 0 8px 24px rgba(217, 119, 87, 0.35);
    }
    .hero-title {
        text-align: center; font-size: 46px; font-weight: 800;
        background: linear-gradient(90deg, #F2F0EC, #D97757);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        letter-spacing: -1.5px; margin-bottom: 6px;
    }
    .hero-sub {
        text-align: center; color: #9A9890; font-size: 16px;
        margin-bottom: 38px;
    }

    /* Stat bar */
    .stat-row { display: flex; gap: 16px; margin-bottom: 42px; }
    .stat-box {
        flex: 1; background: #1E1E1C; border: 1px solid #302F2C;
        border-radius: 14px; padding: 18px; text-align: center;
    }
    .stat-num { font-size: 28px; font-weight: 800; color: #D97757; }
    .stat-label { font-size: 12px; color: #8A8880; margin-top: 4px; }

    /* Feature cards */
    .fcard {
        background: linear-gradient(160deg, #232320, #1C1C1A);
        border: 1px solid #34322F; border-radius: 18px;
        padding: 28px; height: 100%;
        transition: all 0.3s cubic-bezier(.2,.8,.2,1);
        animation: rise 0.5s ease-in backwards;
    }
    .fcard:hover {
        border-color: #D97757; transform: translateY(-8px);
        box-shadow: 0 16px 32px rgba(217, 119, 87, 0.18);
    }
    .fcard:nth-child(1) { animation-delay: 0.05s; }
    @keyframes rise { from { opacity:0; transform: translateY(16px);} to {opacity:1; transform: translateY(0);} }
    .ficon {
        width: 52px; height: 52px; border-radius: 14px;
        background: rgba(217, 119, 87, 0.15);
        display: flex; align-items: center; justify-content: center;
        font-size: 24px; margin-bottom: 16px;
    }
    .ftitle { font-size: 19px; font-weight: 700; color: #F0EEEA; margin-bottom: 8px; }
    .fdesc { font-size: 13.5px; color: #A6A49C; line-height: 1.55; margin-bottom: 16px; min-height: 62px; }
    .fbadge {
        display: inline-block; background: rgba(120, 200, 140, 0.15);
        color: #7CC98F; font-size: 11.5px; font-weight: 600;
        padding: 4px 12px; border-radius: 20px;
    }

    /* Open buttons under the cards */
    [data-testid="stPageLink"] a, [data-testid="stPageLink-NavLink"] {
        border: 1px solid #D97757; border-radius: 10px; font-weight: 600;
        justify-content: center; margin-top: 8px; transition: all 0.2s ease;
    }
    [data-testid="stPageLink"] a:hover, [data-testid="stPageLink-NavLink"]:hover {
        background-color: #D97757; border-color: #D97757;
    }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #141413; }
    [data-testid="stSidebarNav"] a {
        border-radius: 8px; margin: 3px 8px; padding: 8px 10px; font-size: 14.5px;
    }
    [data-testid="stSidebarNav"] a:hover { background-color: #232320; }
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background-color: #2E2420; border-left: 3px solid #D97757;
    }

    .stack-row { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-top: 8px; }
    .stack-pill {
        background: #1E1E1C; border: 1px solid #302F2C; border-radius: 20px;
        padding: 6px 16px; font-size: 12.5px; color: #B0AEA6;
    }
</style>

<div class="hero-badge">🤖</div>
<div class="hero-title">AI Tools Dashboard</div>
<div class="hero-sub">A suite of AI-powered tools built with RAG, Agents, and LLMs</div>

<div class="stat-row">
    <div class="stat-box"><div class="stat-num">12</div><div class="stat-label">AI TOOLS BUILT</div></div>
    <div class="stat-box"><div class="stat-num">4</div><div class="stat-label">FILE FORMATS</div></div>
    <div class="stat-box"><div class="stat-num">2</div><div class="stat-label">AGENT TOOLS</div></div>
    <div class="stat-box"><div class="stat-num">Hard</div><div class="stat-label">LEETCODE SOLVED</div></div>
</div>
""", unsafe_allow_html=True)

PAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")

# card title -> page name (lowercase, no spaces/underscores/number prefix)
PAGE_KEYS = {
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
    "Progress Dashboard": "progressdashboard",
    "Agent Activity": "agentactivity",
}


def find_page(key):
    """Find the real file in pages/ by name, ignoring case, spaces, underscores and 01_ prefixes.
    Returns e.g. 'pages/Quiz_generator.py', or None if it doesn't exist (so Home never crashes)."""
    if not key or not os.path.isdir(PAGES_DIR):
        return None
    for f in sorted(os.listdir(PAGES_DIR)):
        if not f.endswith(".py"):
            continue
        name = re.sub(r"^\d+[_\-\s]*", "", f[:-3]).replace("_", "").replace(" ", "").lower()
        if name == key:
            return f"pages/{f}"
    return None


c1, c2, c3 = st.columns([2, 1, 2])
with c2:
    agent_page = find_page("agentactivity")
    if agent_page:
        st.page_link(agent_page, label="🧭 Agent Activity")

features = [

    ("📚", "Study Assistant", "Upload documents and ask questions. An AI agent decides whether to search your files or the live web."),
    ("🎙️", "Voice Mode", "Talk to the agent instead of typing. Speak in Tamil or English and hear the answer spoken back."),
    ("💻", "Code Bot", "Generates, explains, and debugs code. Verified on a LeetCode Hard problem with optimal complexity."),
    ("📝", "Quiz Generator", "Turns your uploaded documents into an interactive quiz with instant feedback, a final score, mistake review and weak-topic practice."),
    ("🎞️", "PPT Generator", "Type a topic, get a styled, ready-to-present slide deck as a downloadable file."),
    ("🎧", "Audio Explainer", "Type or speak a topic and listen to a spoken explanation in Tamil or English."),
    ("🧠", "Mind Map Generator", "Turns any topic into a visual, branching concept map."),
    ("📄", "Resume Analyzer", "Matches your resume against a job description with a score and suggestions."),
    ("🐛", "AI Code Debugger", "Explains a bug, fixes the code, and runs it to verify the fix actually works."),
    ("🗣️", "Mock Interview", "A multi-round interview from your resume: Technical, Coding and HR. Answer by voice or text and get a score with feedback."),
    ("📊", "Progress Dashboard", "Track quiz scores, interview scores and your weak topics over time with charts."),
    ("🧭", "Agent Activity", "See which tool the agent used for each question: document search, web search, or a direct reply."),

]

cols = st.columns(3)
for i, (icon, title, desc) in enumerate(features):
    with cols[i % 3]:
        st.markdown(f"""
            <div class="fcard">
            <div class="ficon">{icon}</div>
            <div class="ftitle">{title}</div>
            <div class="fdesc">{desc}</div>
            <span class="fbadge">✅ Available</span>
        </div>
        """, unsafe_allow_html=True)
        page = find_page(PAGE_KEYS.get(title, ""))
        if page:
            st.page_link(page, label=f"Open {title} →", use_container_width=True)
    if i % 3 == 2:
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
st.markdown("---")
st.markdown("### 🎤 Speak instead of type")
st.info("Every tool has a built-in mic. Speak your prompt in Tamil or English, or type it, whichever you prefer.")

st.markdown("---")
st.markdown("""
<div class="stack-row">
    <div class="stack-pill">🐍 Python</div>
    <div class="stack-pill">🖥️ Streamlit</div>
    <div class="stack-pill">⚡ Groq</div>
    <div class="stack-pill">🎙️ Whisper</div>
    <div class="stack-pill">🗂️ ChromaDB</div>
    <div class="stack-pill">🔎 Sentence-Transformers</div>
    <div class="stack-pill">🌐 Tavily</div>
    <div class="stack-pill">🔊 gTTS</div>
</div>
""", unsafe_allow_html=True)