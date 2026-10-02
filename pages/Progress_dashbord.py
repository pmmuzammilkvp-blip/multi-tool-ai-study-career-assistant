import streamlit as st
import os
import pandas as pd
from collections import Counter
from shared import get_progress, clear_progress

st.set_page_config(page_title="Progress Dashboard", page_icon="📊", layout="wide")

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
    h1 { letter-spacing: -0.5px; }
    [data-testid="stMetric"] {
        background: #1E1E1C; border: 1px solid #302F2C; border-radius: 14px; padding: 14px 18px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Progress Dashboard")
st.caption("Track your quiz scores, mock interview scores and weak topics")

if os.getenv("DEMO_MODE") == "1":
    st.caption("ℹ️ In this demo, progress is kept only for your current browser session.")
else:
    st.caption("ℹ️ Progress is saved on this computer.")

entries = get_progress()

if not entries:
    st.info("No progress yet. Take a quiz (Quiz Generator) or a Mock Interview and your scores will show up here.")
    st.stop()

quizzes = [e for e in entries if e["kind"] == "quiz"]
interviews = [e for e in entries if e["kind"] == "interview"]


def avg_pct(items):
    return f"{round(sum(e['pct'] for e in items) / len(items))}%" if items else "—"


days_active = len({e["time"][:10] for e in entries})

m1, m2, m3, m4 = st.columns(4)
m1.metric("📝 Quizzes taken", len(quizzes), help="Average score: " + avg_pct(quizzes))
m2.metric("Average quiz score", avg_pct(quizzes))
m3.metric("🗣️ Mock interviews", len(interviews), help="Average score: " + avg_pct(interviews))
m4.metric("📅 Days active", days_active)

st.markdown("---")

left, right = st.columns(2)
with left:
    st.subheader("📝 Quiz scores (%)")
    if quizzes:
        df_q = pd.DataFrame({"Quiz score %": [e["pct"] for e in quizzes]}, index=range(1, len(quizzes) + 1))
        df_q.index.name = "Attempt"
        st.line_chart(df_q)
    else:
        st.caption("No quizzes yet.")

with right:
    st.subheader("🗣️ Interview scores (%)")
    if interviews:
        df_i = pd.DataFrame({"Interview score %": [e["pct"] for e in interviews]}, index=range(1, len(interviews) + 1))
        df_i.index.name = "Attempt"
        st.line_chart(df_i)
    else:
        st.caption("No mock interviews yet.")

st.markdown("---")
st.subheader("⚠️ Weak topics (from quiz mistakes)")
weak_counter = Counter(t for e in quizzes for t in e.get("weak", []))
if weak_counter:
    df_w = pd.DataFrame(
        {"Topic": list(weak_counter.keys()), "Mistakes": list(weak_counter.values())}
    ).sort_values("Mistakes", ascending=False).set_index("Topic")
    st.bar_chart(df_w)
    top = ", ".join(t for t, _ in weak_counter.most_common(3))
    st.write(f"**Focus on:** {top}")
else:
    st.caption("No mistakes recorded yet. Great job, or take a quiz first!")

st.markdown("---")
st.subheader("🕘 History")
rows = [
    {
        "Time": e["time"],
        "Type": "Quiz" if e["kind"] == "quiz" else "Mock Interview",
        "Topic": e.get("topic") or "—",
        "Score": f"{e['score']}/{e['total']}",
        "%": e["pct"],
    }
    for e in reversed(entries)
]
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

if st.button("🗑️ Reset progress"):
    clear_progress()
    st.rerun()