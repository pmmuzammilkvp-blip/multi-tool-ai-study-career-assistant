import html
import streamlit as st

esc = html.escape

# Mountain silhouettes (inline SVG) over a purple dusk gradient
_MOUNTAINS = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 900' "
    "preserveAspectRatio='xMidYMax slice'%3E"
    "%3Cpolygon fill='%237a55b0' fill-opacity='.45' points='0,620 180,520 330,600 520,470 700,590 900,500 1100,610 1300,490 1600,600 1600,900 0,900'/%3E"
    "%3Cpolygon fill='%23452a78' fill-opacity='.75' points='0,720 220,620 400,700 620,590 820,710 1050,620 1250,720 1450,640 1600,700 1600,900 0,900'/%3E"
    "%3Cpolygon fill='%23180d32' fill-opacity='.92' points='0,800 260,730 480,790 760,720 980,800 1250,740 1600,810 1600,900 0,900'/%3E"
    "%3C/svg%3E"
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp, button, input, textarea {font-family: 'Inter', sans-serif !important;}
#MainMenu, footer {visibility: hidden;}
[data-testid="stHeader"] {background: transparent;}
.block-container {position: relative; z-index: 1; padding-top: 2.4rem; max-width: 1080px;}

/* ---------- Wallpaper ---------- */
.stApp {
    background: url("__MOUNTAINS__") bottom center / cover no-repeat fixed,
                linear-gradient(180deg, #140b2e 0%, #26164f 34%, #43276f 58%, #70438f 76%, #1f1238 100%) fixed;
    color: #ECE8F8;
}
.stApp::before {
    content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background: radial-gradient(ellipse at 50% 38%, rgba(0,0,0,0) 30%, rgba(8,4,20,.55) 100%);
}

/* ---------- Glass sidebar ---------- */
[data-testid="stSidebar"] {
    background: rgba(14,10,32,.55); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
    border-right: 1px solid rgba(255,255,255,.10);
}
[data-testid="stSidebarNav"] a {border-radius: 12px; margin: 3px 10px; padding: 9px 12px; font-size: 14.5px; color: #D9D3EE;}
[data-testid="stSidebarNav"] a:hover {background: rgba(255,255,255,.08);}
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.14); color: #fff;
}

/* ---------- Hero ---------- */
.hero {text-align: center; padding: 14px 0 30px 0;}
.orb {
    width: 84px; height: 84px; border-radius: 50%; margin: 0 auto 22px auto;
    background: radial-gradient(circle at 32% 28%, #f6ecff 0%, #c8a8ff 14%, #7c4dff 44%, #2a1170 80%, #150a3a 100%);
    box-shadow: 0 0 36px rgba(150,100,255,.65), 0 0 90px rgba(120,70,255,.35), inset -6px -8px 18px rgba(0,0,0,.45);
    animation: floaty 5s ease-in-out infinite;
}
@keyframes floaty {50% {transform: translateY(-7px);}}
.hero-title {font-size: 34px; font-weight: 600; color: #fff; letter-spacing: -.6px;}
.hero-sub {color: #B9B1D6; font-size: 15px; margin-top: 8px;}

/* ---------- Chips ---------- */
.chips {display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin: 0 0 22px 0;}
.chip {
    padding: 7px 16px; border-radius: 12px; font-size: 13px; color: #E3DDF5;
    background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.13);
    backdrop-filter: blur(14px);
}

/* ---------- Glass cards ---------- */
.card {
    background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12); border-radius: 18px;
    padding: 20px; height: 100%; backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    box-shadow: 0 8px 32px rgba(0,0,0,.28); transition: transform .25s, border-color .25s, background .25s;
}
.card:hover {transform: translateY(-4px); border-color: rgba(167,139,250,.65); background: rgba(255,255,255,.09);}
.card-icon {font-size: 20px; margin-bottom: 10px;}
.card-title {font-size: 15.5px; font-weight: 600; color: #fff; margin-bottom: 6px;}
.card-body {font-size: 13.5px; line-height: 1.6; color: #B9B1D6; min-height: 54px;}
.card-body ul {margin: 0; padding-left: 18px;}
.card-body li {margin-bottom: 5px;}
.stat {text-align: center; padding: 16px;}
.stat-num {font-size: 26px; font-weight: 700; color: #C4B5FD;}
.stat-label {font-size: 11px; letter-spacing: 1.2px; color: #A59DC6; margin-top: 3px;}

/* ---------- Agent timeline ---------- */
.steps {display: flex; justify-content: space-between; margin: 6px 0 24px 0;}
.step {flex: 1; text-align: center; position: relative;}
.step::before {content: ""; position: absolute; top: 17px; left: -50%; width: 100%; height: 2px; background: rgba(255,255,255,.14);}
.step:first-child::before {display: none;}
.step.done::before, .step.active::before {background: linear-gradient(90deg, #8b5cf6, #c4b5fd);}
.dot {
    width: 36px; height: 36px; border-radius: 50%; margin: 0 auto 7px auto; position: relative; z-index: 1;
    display: flex; align-items: center; justify-content: center; font-size: 15px;
    background: rgba(20,12,44,.9); border: 2px solid rgba(255,255,255,.18); color: #A59DC6;
}
.step.done .dot {background: linear-gradient(135deg, #8b5cf6, #6d3df0); border-color: transparent; color: #fff;}
.step.active .dot {border-color: #a78bfa; color: #fff; animation: pulse 1.3s ease-in-out infinite;}
@keyframes pulse {0%,100% {box-shadow: 0 0 0 0 rgba(139,92,246,.7);} 50% {box-shadow: 0 0 0 10px rgba(139,92,246,0);}}
.step-label {font-size: 12.5px; color: #A59DC6;}
.step.done .step-label, .step.active .step-label {color: #fff; font-weight: 600;}

/* ---------- Flashcards ---------- */
.flip {perspective: 1000px; height: 160px; margin-bottom: 16px;}
.flip-inner {position: relative; width: 100%; height: 100%; transition: transform .6s; transform-style: preserve-3d;}
.flip:hover .flip-inner {transform: rotateY(180deg);}
.face {
    position: absolute; inset: 0; border-radius: 18px; padding: 18px; text-align: center;
    display: flex; flex-direction: column; justify-content: center; align-items: center;
    backface-visibility: hidden; -webkit-backface-visibility: hidden;
    border: 1px solid rgba(255,255,255,.14); font-size: 15px; font-weight: 600; color: #fff;
}
.face.front {background: rgba(255,255,255,.07); backdrop-filter: blur(16px);}
.face.back {background: linear-gradient(145deg, rgba(139,92,246,.55), rgba(88,52,190,.5)); transform: rotateY(180deg); font-weight: 500; font-size: 14px;}
.hint {font-size: 10px; letter-spacing: 1.2px; color: #A59DC6; margin-top: 8px; font-weight: 400;}

/* ---------- Mind map ---------- */
.mm-center {
    display: table; margin: 0 auto 18px auto; padding: 12px 30px; border-radius: 30px; font-weight: 600; color: #fff; font-size: 17px;
    background: linear-gradient(135deg, #8b5cf6, #6d3df0); box-shadow: 0 0 30px rgba(139,92,246,.5);
}
.mm-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px;}
.mm-branch {
    background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12); border-left: 3px solid #a78bfa;
    border-radius: 14px; padding: 14px; backdrop-filter: blur(16px);
}
.mm-title {font-weight: 600; color: #fff; margin-bottom: 8px; font-size: 14.5px;}
.mm-chip {display: inline-block; margin: 0 6px 6px 0; padding: 4px 10px; border-radius: 12px; font-size: 12.5px; background: rgba(167,139,250,.18); color: #DDD2FF;}

/* ---------- Streamlit widgets ---------- */
.stButton > button, .stDownloadButton > button {
    border: none; border-radius: 12px; font-weight: 600; padding: 9px 24px; color: #fff;
    background: linear-gradient(135deg, #8b5cf6, #6d3df0); box-shadow: 0 6px 22px rgba(109,61,240,.4); transition: all .2s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {color: #fff; transform: translateY(-2px); box-shadow: 0 10px 28px rgba(139,92,246,.6);}
[data-baseweb="input"] > div, [data-baseweb="textarea"], [data-baseweb="select"] > div {
    background: rgba(255,255,255,.07) !important; border: 1px solid rgba(255,255,255,.14) !important; border-radius: 14px !important;
    backdrop-filter: blur(14px);
}
[data-testid="stChatInput"] {background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.14); border-radius: 20px; backdrop-filter: blur(20px);}
[data-testid="stChatInput"] > div {background: transparent;}
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,.055); border: 1px solid rgba(255,255,255,.11); border-radius: 18px; padding: 16px 20px;
    backdrop-filter: blur(16px); margin-bottom: 14px;
}
[data-testid="stAlert"] {background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.13); border-radius: 14px; backdrop-filter: blur(14px);}
[data-testid="stExpander"] {background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.12); border-radius: 14px;}
[data-testid="stFileUploaderDropzone"] {background: rgba(255,255,255,.06); border: 1px dashed rgba(255,255,255,.25); border-radius: 16px;}
button[data-baseweb="tab"] {font-weight: 500; font-size: 14.5px; color: #B9B1D6;}
button[data-baseweb="tab"][aria-selected="true"] {color: #fff;}
[data-baseweb="tab-highlight"] {background: #a78bfa !important; height: 3px !important; border-radius: 3px;}
[data-baseweb="tab-border"] {background: rgba(255,255,255,.12) !important;}
[data-testid="stPageLink"] a {
    border: 1px solid rgba(255,255,255,.16); border-radius: 12px; justify-content: center; margin-top: 8px;
    background: rgba(255,255,255,.06); transition: all .2s ease;
}
[data-testid="stPageLink"] a:hover {background: rgba(139,92,246,.45); border-color: #a78bfa;}
</style>
""".replace("__MOUNTAINS__", _MOUNTAINS)


def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title, subtitle, icon=""):
    st.markdown(
        f'<div class="hero"><div class="orb"></div>'
        f'<div class="hero-title">{esc(title)}</div><div class="hero-sub">{esc(subtitle)}</div></div>',
        unsafe_allow_html=True,
    )


def chips(items):
    st.markdown(
        '<div class="chips">' + "".join(f'<span class="chip">{esc(i)}</span>' for i in items) + "</div>",
        unsafe_allow_html=True,
    )


def card(title, body="", icon="", bullets=None):
    inner = esc(body)
    if bullets:
        inner += "<ul>" + "".join(f"<li>{esc(str(b))}</li>" for b in bullets) + "</ul>"
    return (
        f'<div class="card"><div class="card-icon">{icon}</div><div class="card-title">{esc(title)}</div>'
        f'<div class="card-body">{inner}</div></div>'
    )


def stat_tile(num, label):
    return f'<div class="card stat"><div class="stat-num">{esc(str(num))}</div><div class="stat-label">{esc(label)}</div></div>'


def stepper(steps, current):
    """steps: list of (icon, label). current: running step index (len(steps) = all done)."""
    out = '<div class="steps">'
    for i, (icon, label) in enumerate(steps):
        cls = "done" if i < current else ("active" if i == current else "")
        mark = "✓" if i < current else icon
        out += f'<div class="step {cls}"><div class="dot">{mark}</div><div class="step-label">{esc(label)}</div></div>'
    return out + "</div>"


def flashcard(question, answer):
    return (
        f'<div class="flip"><div class="flip-inner">'
        f'<div class="face front"><div>{esc(question)}</div><div class="hint">HOVER TO FLIP</div></div>'
        f'<div class="face back">{esc(answer)}</div></div></div>'
    )


def mindmap(center, branches):
    out = f'<div class="mm-center">{esc(center)}</div><div class="mm-grid">'
    for b in branches:
        chip_html = "".join(f'<span class="mm-chip">{esc(str(c))}</span>' for c in b.get("children", []))
        out += f'<div class="mm-branch"><div class="mm-title">{esc(str(b.get("title", "")))}</div>{chip_html}</div>'
    return out + "</div>"