import streamlit as st
from shared import get_agent_stats

st.set_page_config(page_title="Agent Activity", page_icon="🧭", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2.5rem; max-width: 900px; }
    [data-testid="stSidebar"] { background-color: #171716; }
    [data-testid="stSidebarNav"] a { border-radius: 8px; margin: 3px 8px; padding: 8px 10px; font-size: 14.5px; }
    [data-testid="stSidebarNav"] a:hover { background-color: #2A2A28; }
    [data-testid="stSidebarNav"] a[aria-current="page"] { background-color: #2E2420; border-left: 3px solid #D97757; }
    .tool-card { background: #1E1E1C; border: 1px solid #302F2C; border-radius: 14px; padding: 20px; text-align: center; }
    .tool-num { font-size: 32px; font-weight: 800; color: #D97757; }
    .tool-label { font-size: 13px; color: #9A9890; margin-top: 4px; }
    .log-row { background: #1E1E1C; border: 1px solid #302F2C; border-radius: 10px; padding: 10px 16px; margin-bottom: 8px; font-size: 13.5px; }
    .log-tool { color: #D97757; font-weight: 600; }
    .log-time { color: #7A7870; font-size: 11.5px; float: right; }
</style>
""", unsafe_allow_html=True)

st.title("🧭 Agent Activity")
st.caption("How the Study Assistant agent has been deciding between its tools")

stats = get_agent_stats()
counts = stats.get("counts", {})
log = stats.get("log", [])
total = sum(counts.values())

st.markdown(f"### Total agent decisions: **{total}**")

cols = st.columns(len(counts))
for i, (tool, count) in enumerate(counts.items()):
    with cols[i]:
        st.markdown(f"""
        <div class="tool-card">
            <div class="tool-num">{count}</div>
            <div class="tool-label">{tool.upper()}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("### Recent Activity")

if not log:
    st.caption("No questions asked yet. Go to Study Assistant and ask something!")
else:
    for entry in log:
        st.markdown(f"""
        <div class="log-row">
            <span class="log-tool">🔧 {entry['tool']}</span>
            <span class="log-time">{entry['timestamp']}</span><br>
            {entry['question']}
        </div>
        """, unsafe_allow_html=True)