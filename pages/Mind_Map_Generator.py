import streamlit as st
from groq import Groq
import os, json, re, textwrap
from html import escape
from dotenv import load_dotenv
from shared import voice_or_text

load_dotenv()

st.set_page_config(page_title="Mind Map Generator", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2.5rem; max-width: 1100px; }
    .stButton button {
        border-radius: 10px; border: 1px solid #D97757; font-weight: 600;
        padding: 6px 18px; transition: all 0.2s ease;
    }
    .stButton button:hover { background-color: #D97757; border-color: #D97757; transform: scale(1.02); }
    [data-testid="stSidebar"] { background-color: #171716; }
    [data-testid="stSidebarNav"] a { border-radius: 8px; margin: 3px 8px; padding: 8px 10px; font-size: 14.5px; }
    [data-testid="stSidebarNav"] a:hover { background-color: #2A2A28; }
    [data-testid="stSidebarNav"] a[aria-current="page"] { background-color: #2E2420; border-left: 3px solid #D97757; }

    .central-node {
        background: linear-gradient(135deg, #D97757, #E8A87C); color: white;
        font-weight: 700; font-size: 18px; text-align: center;
        border-radius: 14px; padding: 16px 24px; margin: 0 auto 0 auto; width: fit-content;
        box-shadow: 0 8px 20px rgba(217,119,87,0.3);
    }
    .connector { width: 2px; height: 28px; background: #3A3A38; margin: 0 auto; }
    .branch-row { display: flex; gap: 18px; justify-content: center; flex-wrap: wrap; }
    .branch-col { flex: 1; min-width: 200px; max-width: 260px; }
    .branch-title {
        background: #232320; border: 1px solid #D97757; border-radius: 10px;
        padding: 10px 14px; font-weight: 700; color: #F0EEEA; text-align: center; margin-bottom: 10px;
    }
    .leaf {
        background: #1E1E1C; border: 1px solid #302F2C; border-radius: 8px;
        padding: 8px 12px; margin-bottom: 8px; font-size: 13.5px; color: #C8C6BE;
        border-left: 3px solid #D97757;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 Mind Map Generator")
st.caption("Turn any topic into a visual concept map")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------- download helpers ----------------
def _wrap(text, width):
    return textwrap.wrap(str(text), width=width) or [""]


def build_svg(data):
    """Mind map as a standalone SVG image (opens in any browser, can be inserted into PPT or Word)."""
    branches = data.get("branches", [])
    n = max(len(branches), 1)
    col_w, gap, pad = 260, 24, 30
    width = max(pad * 2 + n * col_w + (n - 1) * gap, 460)
    cx = width / 2

    out = []
    central_lines = _wrap(data.get("central", ""), 32)[:3]
    cen_w, cen_h, cen_y = 400, 26 + 24 * len(central_lines), 30
    out.append(f'<rect x="{cx - cen_w / 2}" y="{cen_y}" width="{cen_w}" height="{cen_h}" rx="16" fill="#D97757"/>')
    for k, line in enumerate(central_lines):
        out.append(
            f'<text x="{cx}" y="{cen_y + 32 + 24 * k}" text-anchor="middle" font-size="20" '
            f'font-weight="700" fill="#FFFFFF">{escape(line)}</text>'
        )

    title_y = cen_y + cen_h + 60
    bottom = title_y
    for i, b in enumerate(branches):
        x = pad + i * (col_w + gap)
        bx = x + col_w / 2
        t_lines = _wrap(b.get("title", ""), 24)[:2]
        t_h = 20 + 22 * len(t_lines)

        y1 = cen_y + cen_h
        out.append(
            f'<path d="M {cx} {y1} C {cx} {y1 + 30}, {bx} {title_y - 30}, {bx} {title_y}" '
            f'fill="none" stroke="#5A5A56" stroke-width="2"/>'
        )
        out.append(
            f'<rect x="{x}" y="{title_y}" width="{col_w}" height="{t_h}" rx="10" '
            f'fill="#232320" stroke="#D97757" stroke-width="1.5"/>'
        )
        for k, line in enumerate(t_lines):
            out.append(
                f'<text x="{bx}" y="{title_y + 26 + 22 * k}" text-anchor="middle" font-size="16" '
                f'font-weight="700" fill="#F0EEEA">{escape(line)}</text>'
            )

        y = title_y + t_h + 16
        for child in b.get("children", []):
            c_lines = _wrap(child, 30)[:4]
            c_h = 18 + 20 * len(c_lines)
            out.append(f'<rect x="{x}" y="{y}" width="{col_w}" height="{c_h}" rx="8" fill="#1E1E1C" stroke="#302F2C"/>')
            out.append(f'<rect x="{x}" y="{y}" width="4" height="{c_h}" rx="2" fill="#D97757"/>')
            for k, line in enumerate(c_lines):
                out.append(f'<text x="{x + 16}" y="{y + 24 + 20 * k}" font-size="14" fill="#C8C6BE">{escape(line)}</text>')
            y += c_h + 10
        bottom = max(bottom, y)

    height = bottom + pad
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Segoe UI, Arial, sans-serif">'
        '<rect width="100%" height="100%" fill="#1A1A18"/>' + "".join(out) + "</svg>"
    )


MAP_CSS = """
body { background: #1A1A18; font-family: 'Segoe UI', Arial, sans-serif; padding: 30px; }
.central-node {
    background: linear-gradient(135deg, #D97757, #E8A87C); color: white;
    font-weight: 700; font-size: 18px; text-align: center;
    border-radius: 14px; padding: 16px 24px; margin: 0 auto; width: fit-content;
}
.connector { width: 2px; height: 28px; background: #3A3A38; margin: 0 auto; }
.branch-row { display: flex; gap: 18px; justify-content: center; flex-wrap: wrap; }
.branch-col { flex: 1; min-width: 200px; max-width: 260px; }
.branch-title {
    background: #232320; border: 1px solid #D97757; border-radius: 10px;
    padding: 10px 14px; font-weight: 700; color: #F0EEEA; text-align: center; margin-bottom: 10px;
}
.leaf {
    background: #1E1E1C; border: 1px solid #302F2C; border-radius: 8px;
    padding: 8px 12px; margin-bottom: 8px; font-size: 13.5px; color: #C8C6BE;
    border-left: 3px solid #D97757;
}
"""


def build_html_file(data):
    """Mind map as a standalone web page (open in a browser, or print it to PDF)."""
    central = escape(str(data.get("central", "Mind Map")))
    body = "<div class='branch-row'>"
    for b in data.get("branches", []):
        body += f"<div class='branch-col'><div class='branch-title'>{escape(str(b.get('title', '')))}</div>"
        for child in b.get("children", []):
            body += f"<div class='leaf'>{escape(str(child))}</div>"
        body += "</div>"
    body += "</div>"
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{central}</title><style>{MAP_CSS}</style></head><body>"
        f"<div class='central-node'>{central}</div><div class='connector'></div>{body}</body></html>"
    )


topic = voice_or_text("Enter a topic:", key="mindmap")

if st.button("Generate Mind Map"):
    if not topic:
        st.warning("Please enter a topic first.")
    else:
        with st.spinner("Mapping it out..."):
            prompt = f"""Create a mind map structure for the topic: "{topic}"

Return ONLY valid JSON (no markdown, no code fences) in this exact format:
{{
  "central": "Short central topic name",
  "branches": [
    {{"title": "Branch name", "children": ["point 1", "point 2", "point 3"]}}
  ]
}}

Create 4-6 branches, each with 2-4 short children (under 8 words each)."""

            try:
                response = groq_client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=[
                        {"role": "system", "content": "You output only valid JSON for mind maps, nothing else."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=900,
                )
                raw = response.choices[0].message.content.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                st.session_state.mindmap = json.loads(raw)
            except Exception as e:
                st.error(f"Couldn't generate the mind map: {e}")

if "mindmap" in st.session_state:
    data = st.session_state.mindmap
    st.markdown(f"<div class='central-node'>{data['central']}</div>", unsafe_allow_html=True)
    st.markdown("<div class='connector'></div>", unsafe_allow_html=True)

    html = "<div class='branch-row'>"
    for b in data.get("branches", []):
        html += f"<div class='branch-col'><div class='branch-title'>{b['title']}</div>"
        for child in b.get("children", []):
            html += f"<div class='leaf'>{child}</div>"
        html += "</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    # download the mind map
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    file_base = re.sub(r"[^A-Za-z0-9_-]+", "_", str(data.get("central", ""))).strip("_") or "mindmap"
    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "📥 Download as image (SVG)",
            data=build_svg(data),
            file_name=f"{file_base}_mindmap.svg",
            mime="image/svg+xml",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "📥 Download as web page (HTML)",
            data=build_html_file(data),
            file_name=f"{file_base}_mindmap.html",
            mime="text/html",
            use_container_width=True,
        )