import streamlit as st
from groq import Groq
import os, json
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