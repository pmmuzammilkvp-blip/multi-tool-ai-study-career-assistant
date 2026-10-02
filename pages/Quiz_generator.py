import streamlit as st
from groq import Groq
import os
import re
import json
from collections import Counter
from dotenv import load_dotenv
from shared import search_knowledge_base, voice_or_text, log_progress

load_dotenv()

st.set_page_config(page_title="Quiz Generator", page_icon="📝", layout="wide")

st.markdown("""
<style>
    .block-container {
        padding-top: 2.5rem;
        max-width: 900px;
    }
    [data-testid="stChatMessage"] {
        border-radius: 18px;
        padding: 18px 22px;
        margin-bottom: 18px;
        border: 1px solid #2E2E2C;
        animation: fadeIn 0.3s ease-in;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    [data-testid="stChatInput"] textarea {
        border-radius: 14px;
        font-size: 15px;
    }
    .stButton button {
        border-radius: 10px;
        border: 1px solid #D97757;
        font-weight: 600;
        padding: 6px 18px;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        background-color: #D97757;
        border-color: #D97757;
        transform: scale(1.02);
    }
    [data-testid="stSidebar"] {
        background-color: #171716;
    }
    [data-testid="stSidebarNav"] a {
        border-radius: 8px;
        margin: 3px 8px;
        padding: 8px 10px;
        font-size: 14.5px;
    }
    [data-testid="stSidebarNav"] a:hover {
        background-color: #2A2A28;
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background-color: #2E2420;
        border-left: 3px solid #D97757;
    }
    h1 {
        letter-spacing: -0.5px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📝 Quiz Generator")
st.caption("Generate quiz questions from your uploaded documents (Study Assistant page)")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


DEFAULTS = {
    "quiz_questions": [],
    "quiz_idx": 0,
    "quiz_score": 0,
    "quiz_submitted": False,
    "quiz_last_ok": None,
    "quiz_done": False,
    "quiz_wrong": [],  # NEW: list of mistakes for review + weak topics
    "quiz_logged": False,  # NEW: score saved to Progress Dashboard once
}
for k, v in DEFAULTS.items():
    # copy lists so DEFAULTS itself never gets modified
    st.session_state.setdefault(k, list(v) if isinstance(v, list) else v)


def reset_quiz():
    for k, v in DEFAULTS.items():
        st.session_state[k] = [] if isinstance(v, list) else v


def parse_quiz_json(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = text.replace("```json", "").replace("```", "").strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("No JSON list found")
    data = json.loads(text[start:end + 1])
    cleaned = []
    for q in data:
        if all(k in q for k in ("question", "options", "answer")) and len(q["options"]) >= 2:
            q["subtopic"] = (q.get("subtopic") or "General").strip()  # NEW
            cleaned.append(q)
    if not cleaned:
        raise ValueError("No valid questions")
    return cleaned


def correct_index(q):
    ans = str(q["answer"]).strip()
    opts = q["options"]
    if len(ans) == 1 and ans.upper() in "ABCD":
        return "ABCD".index(ans.upper())
    # "B) text" or "B. text" format
    m = re.match(r"^([ABCD])[\)\.\:]", ans.upper())
    if m:
        return "ABCD".index(m.group(1))
    for i, o in enumerate(opts):
        if o.strip().lower() == ans.lower():
            return i
    return 0


def generate_quiz(topic, num_questions):
    chunks, metadatas = search_knowledge_base(topic, n_results=5)
    if not chunks:
        return None
    context = "\n\n".join(chunks)

    prompt = f"""Based on the following content, create {num_questions} multiple-choice questions to test understanding.

Content:
{context}

Return ONLY a valid JSON array, no extra text, no markdown. Each item must be:
{{"question": "...", "options": ["option text 1", "option text 2", "option text 3", "option text 4"], "answer": "exact text of the correct option", "subtopic": "short 2-4 word name of the concept this question tests", "explanation": "brief explanation of why the answer is correct"}}

Do not put A/B/C/D labels inside the options text."""

    response = groq_client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {"role": "system", "content": "You are a quiz-generating assistant. Create clear, accurate multiple-choice questions based only on the provided content. Output valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=3000
    )
    return parse_quiz_json(response.choices[0].message.content)


def start_quiz(topic, num_questions):
    """Generate a quiz and open it. Used by both 'Generate' and 'Practice weak topics'."""
    with st.spinner("Generating quiz..."):
        try:
            questions = generate_quiz(topic, num_questions)
        except Exception:
            questions = "error"
    if questions is None:
        st.warning("No content found for this topic. Upload documents in Study Assistant first.")
    elif questions == "error":
        st.error("Can't generate the quiz. Please enter a topic related to your uploaded notes and files.")
    else:
        reset_quiz()
        st.session_state.quiz_questions = questions
        st.session_state.quiz_topic = topic  # NEW: used by Progress Dashboard
        st.rerun()


# ---------------- 1. Generate screen ----------------
if not st.session_state.quiz_questions:
    topic = voice_or_text("Enter a topic from your uploaded documents:", key="quiz")
    num_questions = st.slider("Number of questions", min_value=3, max_value=10, value=5)

    if st.button("Generate Quiz"):
        if not topic:
            st.warning("Please enter a topic first.")
        else:
            start_quiz(topic, num_questions)

# ---------------- 3. Result screen ----------------
elif st.session_state.quiz_done:
    total = len(st.session_state.quiz_questions)
    score = st.session_state.quiz_score
    wrong = st.session_state.quiz_wrong

    st.header(f"🎯 Score: {score}/{total}")
    st.progress(score / total)
    pct = score / total
    if pct == 1:
        st.balloons()
        st.success("Perfect! 🔥")
    elif pct >= 0.6:
        st.info("GOOD try! 👍")
    else:
        st.warning("TRY HARD 💪")

    weak = Counter(w["subtopic"] for w in wrong)

    # NEW: save this result for the Progress Dashboard (only once per quiz)
    if not st.session_state.quiz_logged:
        log_progress(
            "quiz", score, total,
            topic=st.session_state.get("quiz_topic", ""),
            weak=[w["subtopic"] for w in wrong],
        )
        st.session_state.quiz_logged = True

    # NEW: weak topics summary
    if weak:
        st.subheader("⚠️ Weak topics")
        for topic_name, count in weak.most_common():
            st.write(f"- **{topic_name}** — {count} mistake(s)")

        # NEW: mistake review
        st.subheader("📖 Review your mistakes")
        for n, w in enumerate(wrong, 1):
            with st.expander(f"❌ {n}. {w['question']}"):
                st.write(f"**Your answer:** {w['your']}")
                st.write(f"**Correct answer:** {w['correct']}")
                if w["explanation"]:
                    st.info(f"💡 {w['explanation']}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 New Quiz"):
            reset_quiz()
            st.rerun()
    with col2:
        # NEW: new quiz focused on weak topics
        if weak and st.button("🎯 Practice weak topics"):
            start_quiz(", ".join(weak.keys()), total)

# ---------------- 2. Question screen ----------------
else:
    quiz = st.session_state.quiz_questions
    i = st.session_state.quiz_idx
    q = quiz[i]
    ci = correct_index(q)

    st.progress(i / len(quiz))
    st.subheader(f"Q{i + 1}/{len(quiz)}: {q['question']}")

    choice = st.radio(
        "Choose one:", q["options"], index=None,
        key=f"quiz_choice_{i}", disabled=st.session_state.quiz_submitted
    )

    if not st.session_state.quiz_submitted:
        if st.button("Submit", disabled=choice is None):
            ok = q["options"].index(choice) == ci
            st.session_state.quiz_last_ok = ok
            st.session_state.quiz_submitted = True
            if ok:
                st.session_state.quiz_score += 1
            else:
                # NEW: remember the mistake
                st.session_state.quiz_wrong.append({
                    "question": q["question"],
                    "your": choice,
                    "correct": q["options"][ci],
                    "explanation": q.get("explanation", ""),
                    "subtopic": q.get("subtopic", "General"),
                })
            st.rerun()
    else:
        if st.session_state.quiz_last_ok:
            st.success("✅ Correct!")
        else:
            st.error(f"❌ Wrong. Correct answer: {q['options'][ci]}")
        if q.get("explanation"):
            st.info(f"💡 {q['explanation']}")

        label = "Next ➡️" if i + 1 < len(quiz) else "Finish 🏁"
        if st.button(label):
            st.session_state.quiz_submitted = False
            st.session_state.quiz_last_ok = None
            if i + 1 < len(quiz):
                st.session_state.quiz_idx += 1
            else:
                st.session_state.quiz_done = True
            st.rerun()