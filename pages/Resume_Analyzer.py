import streamlit as st
from groq import Groq
import os, json
from dotenv import load_dotenv
from loaders import load_file
from shared import voice_or_text

load_dotenv()

st.set_page_config(page_title="Resume Analyzer", page_icon="📄", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2.5rem; max-width: 1000px; }
    .stButton button {
        border-radius: 10px; border: 1px solid #D97757; font-weight: 600;
        padding: 6px 18px; transition: all 0.2s ease;
    }
    .stButton button:hover { background-color: #D97757; border-color: #D97757; transform: scale(1.02); }
    [data-testid="stSidebar"] { background-color: #171716; }
    [data-testid="stSidebarNav"] a { border-radius: 8px; margin: 3px 8px; padding: 8px 10px; font-size: 14.5px; }
    [data-testid="stSidebarNav"] a:hover { background-color: #2A2A28; }
    [data-testid="stSidebarNav"] a[aria-current="page"] { background-color: #2E2420; border-left: 3px solid #D97757; }

    .score-card {
        background: #1E1E1C; border: 1px solid #302F2C; border-radius: 16px;
        padding: 24px; text-align: center; margin-bottom: 20px;
    }
    .score-num { font-size: 48px; font-weight: 800; color: #D97757; }
    .score-label { font-size: 13px; color: #9A9890; margin-top: 4px; }
    .skill-pill {
        display: inline-block; border-radius: 16px; padding: 5px 14px;
        margin: 4px; font-size: 12.5px; font-weight: 600;
    }
    .matched { background: rgba(120,200,140,0.15); color: #7CC98F; }
    .missing { background: rgba(220,100,90,0.15); color: #E08478; }
</style>
""", unsafe_allow_html=True)

st.title("📄 Resume Analyzer")
st.caption("Match your resume against a job description")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

resume_file = st.file_uploader("Upload your resume", type=["pdf", "docx", "txt"])
job_desc = voice_or_text("Paste the job description", key="resume", height=180)

if st.button("Analyze Match"):
    if not resume_file or not job_desc:
        st.warning("Please upload a resume and paste a job description.")
    else:
        with st.spinner("Analyzing..."):
            os.makedirs("data", exist_ok=True)
            temp_path = os.path.join("data", resume_file.name)
            with open(temp_path, "wb") as f:
                f.write(resume_file.getbuffer())
            resume_text = load_file(temp_path)

            prompt = f"""Compare this resume against the job description.

RESUME:
{resume_text[:4000]}

JOB DESCRIPTION:
{job_desc[:2000]}

Return ONLY valid JSON (no markdown, no code fences) in this exact format:
{{
  "match_score": <integer 0-100>,
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1", "skill2"],
  "suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"]
}}"""

            try:
                response = groq_client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=[
                        {"role": "system", "content": "You are a resume-matching assistant. Output only valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=900,
                )
                raw = response.choices[0].message.content.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                st.session_state.resume_result = json.loads(raw)
            except Exception as e:
                st.error(f"Couldn't analyze: {e}")

if "resume_result" in st.session_state:
    r = st.session_state.resume_result
    st.markdown(f"""
    <div class="score-card">
        <div class="score-num">{r['match_score']}%</div>
        <div class="score-label">MATCH SCORE</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**✅ Matched Skills**")
        pills = "".join([f"<span class='skill-pill matched'>{s}</span>" for s in r.get("matched_skills", [])])
        st.markdown(pills, unsafe_allow_html=True)
    with col2:
        st.markdown("**❌ Missing Skills**")
        pills = "".join([f"<span class='skill-pill missing'>{s}</span>" for s in r.get("missing_skills", [])])
        st.markdown(pills, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**💡 Suggestions**")
    for s in r.get("suggestions", []):
        st.markdown(f"- {s}")