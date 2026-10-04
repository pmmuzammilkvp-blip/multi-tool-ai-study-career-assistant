import streamlit as st
from groq import Groq, RateLimitError
import os, re, subprocess, tempfile
from dotenv import load_dotenv
from shared import voice_or_text

load_dotenv()

st.set_page_config(page_title="AI Code Debugger", page_icon="🐛", layout="wide")

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
    .output-box {
        background: #1E1E1C; border: 1px solid #302F2C; border-radius: 10px;
        padding: 14px; font-family: Consolas, monospace; font-size: 13px; white-space: pre-wrap;
    }
    .ok { border-left: 4px solid #7CC98F; }
    .err { border-left: 4px solid #E08478; }
</style>
""", unsafe_allow_html=True)

st.title("🐛 AI Code Debugger")
st.caption("Paste code (and the error, if you have one) — get an explanation, a fix, and run it to verify")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

code_input = st.text_area("Your Python code", height=220, placeholder="Paste the code that's not working...")
error_input = voice_or_text(
    "Error message (optional)", key="debugger", height=100,
    placeholder="Paste the traceback here, if you have one...",
)

if st.button("Debug It"):
    if not code_input:
        st.warning("Please paste some code first.")
    else:
        with st.spinner("Debugging..."):
            prompt = f"""Here is Python code that has a problem:

```python
{code_input}
```

Error (if any): {error_input or "Not provided — find the bug yourself."}

Explain the bug in 2-3 sentences, then give the complete corrected code in a single python code block.
Format: explanation first, then exactly one ```python fenced code block with the full corrected code."""

            try:
                response = groq_client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=[
                        {"role": "system", "content": "You are an expert Python debugger. Be concise and precise."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=900,
                )
            except RateLimitError:
                st.warning("⏳ The AI usage limit was reached. Please wait about a minute and click Debug It again.")
                st.stop()
            reply = response.choices[0].message.content

            match = re.search(r"```python\s*(.*?)```", reply, re.DOTALL)
            fixed_code = match.group(1).strip() if match else None
            explanation = reply[:match.start()].strip() if match else reply

            st.session_state.debug_explanation = explanation
            st.session_state.debug_fixed_code = fixed_code

if "debug_explanation" in st.session_state:
    st.markdown("### 🔍 What's wrong")
    st.write(st.session_state.debug_explanation)

    if st.session_state.debug_fixed_code:
        st.markdown("### ✅ Fixed code")
        st.code(st.session_state.debug_fixed_code, language="python")

        if os.getenv("DEMO_MODE") == "1":
            st.info("▶️ Running code is turned off in the public demo for security. Run the app locally to use it.")
        elif st.button("▶️ Run fixed code to verify"):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(st.session_state.debug_fixed_code)
                temp_path = f.name
            try:
                result = subprocess.run(
                    ["python", temp_path], capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    st.markdown(f"<div class='output-box ok'>✅ Ran successfully\n\n{result.stdout or '(no output)'}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='output-box err'>❌ Still has an error\n\n{result.stderr}</div>", unsafe_allow_html=True)
            except subprocess.TimeoutExpired:
                st.error("Code took too long to run (10s timeout) — might have an infinite loop.")
            finally:
                os.unlink(temp_path)