import streamlit as st
from groq import Groq
from gtts import gTTS
import io
import os
import re
import json
import time
import tempfile
from dotenv import load_dotenv
from loaders import load_file
from shared import voice_or_text, log_progress

load_dotenv()

st.set_page_config(page_title="Mock Interview", page_icon="🗣️", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2.5rem; max-width: 900px; }
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
    .score-card {
        background: #1E1E1C; border: 1px solid #302F2C; border-radius: 16px;
        padding: 24px; text-align: center; margin-bottom: 20px;
    }
    .score-num { font-size: 48px; font-weight: 800; color: #D97757; }
    .score-label { font-size: 13px; color: #9A9890; margin-top: 4px; }
    .q-card {
        background: #1E1E1C; border: 1px solid #302F2C; border-left: 4px solid #D97757;
        border-radius: 12px; padding: 16px 20px; margin-bottom: 14px; font-size: 17px;
    }
    .round-badge {
        display: inline-block; background: rgba(217, 119, 87, 0.15); color: #D97757;
        font-size: 13px; font-weight: 700; padding: 5px 14px; border-radius: 14px; margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🗣️ Mock Interview")
st.caption("A multi-round interview from your resume: Technical, Coding and HR. Answer by voice or text.")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CHAT_MODEL = "qwen/qwen3.8-27b"
MAX_OUT = 900  # keep at or below your Groq output-tokens-per-minute limit
LANG_CODES = {"English": "en", "Tamil": "ta"}
LANG_RULES = {
    "English": "",
    "Tamil": "Write ONLY in Tamil script (தமிழ்). Keep English technical terms in Tamil script the way they sound.",
}
CODE_LANGS = {"Python": "python", "Java": "java", "C++": "cpp", "JavaScript": "javascript"}

# fixed round order
ROUNDS = {
    "technical": ("Technical", "🛠️"),
    "coding": ("Coding", "💻"),
    "hr": ("HR / Behavioural", "🤝"),
}
ROUND_ORDER = ["technical", "coding", "hr"]

DEFAULTS = {
    "mi_items": [],          # every question of every round, in order
    "mi_round_keys": [],     # rounds chosen by the user, in order
    "mi_idx": 0,
    "mi_results": [],
    "mi_submitted": False,
    "mi_done": False,
    "mi_logged": False,
    "mi_resume_text": "",
    "mi_role": "",
    "mi_language": "English",
    "mi_code_lang": "Python",
    "mi_read_aloud": True,
    "mi_audio": {},
    "mi_toast": None,
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, type(v)() if isinstance(v, (list, dict)) else v)


def reset_interview():
    for k, v in DEFAULTS.items():
        st.session_state[k] = type(v)() if isinstance(v, (list, dict)) else v


# ---------------- helpers ----------------
def clean(text):
    # removes finished and unfinished <think> blocks
    return re.sub(r"<think>.*?(</think>|$)", "", text, flags=re.DOTALL).strip()


def parse_json(text, opener, closer):
    text = clean(text).replace("```json", "").replace("```", "").strip()
    start, end = text.find(opener), text.rfind(closer)
    if start == -1 or end == -1:
        raise ValueError("No JSON found")
    return json.loads(text[start:end + 1])


def ask(system, prompt, max_tokens=MAX_OUT):
    # Groq's free plan allows only ~1000 output tokens per minute for this model,
    # so a single request can never ask for more than MAX_OUT.
    max_tokens = min(max_tokens, MAX_OUT)
    for attempt in range(3):
        try:
            resp = groq_client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content
        except Exception as e:
            # per-minute limit reached: wait a little and try again
            if "429" in str(e) and attempt < 2:
                time.sleep(20)
                continue
            raise


def read_resume(uploaded):
    # temp file, deleted right after reading (resume is not kept on the server)
    suffix = os.path.splitext(uploaded.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        path = tmp.name
    try:
        return load_file(path)
    finally:
        os.unlink(path)


def generate_round(round_key, resume_text, role, n, language, code_lang):
    """Returns a list of question items for one round."""
    role_line = f" for the role of {role}" if role else ""
    resume = resume_text[:4000]
    rule = LANG_RULES[language]

    if round_key == "technical":
        prompt = f"""You are a technical interviewer{role_line}. Read this resume and write {n} technical interview questions
about the candidate's own skills, tools and projects. Order from easy to hard. Each question is one or two sentences, in {language}.
{rule}

RESUME:
{resume}

Return ONLY a valid JSON array of {n} strings."""
        data = parse_json(ask("You write fair, clear interview questions. Output only valid JSON.", prompt), "[", "]")
        return [{"round_key": "technical", "type": "text", "question": str(q).strip()} for q in data if str(q).strip()][:n]

    if round_key == "hr":
        prompt = f"""You are an HR interviewer{role_line}. Read this resume and write {n} HR / behavioural questions
(teamwork, challenges, strengths and weaknesses, career goals, why this role). Make them relevant to this candidate.
Each question is one or two sentences, in {language}.
{rule}

RESUME:
{resume}

Return ONLY a valid JSON array of {n} strings."""
        data = parse_json(ask("You write fair, clear interview questions. Output only valid JSON.", prompt), "[", "]")
        return [{"round_key": "hr", "type": "text", "question": str(q).strip()} for q in data if str(q).strip()][:n]

    # coding round
    prompt = f"""You are a coding interviewer{role_line}. Write {n} coding problem(s) for a candidate with this resume.
Difficulty: easy to medium, a classic interview problem that can be solved in {code_lang} in under 25 lines.
Write the title, statement and example in {language}.
{rule}

RESUME:
{resume}

Return ONLY a valid JSON array of {n} objects in this exact format:
[{{"title": "short title", "statement": "clear problem statement", "example": "Input: ...  Output: ..."}}]"""
    data = parse_json(ask("You write clear coding interview problems. Output only valid JSON.", prompt, 2000), "[", "]")
    items = []
    for p in data:
        if isinstance(p, dict) and p.get("statement"):
            items.append({
                "round_key": "coding", "type": "coding",
                "title": str(p.get("title", "Coding problem")).strip(),
                "question": str(p["statement"]).strip(),
                "example": str(p.get("example", "")).strip(),
            })
    return items[:n]


def _score(fb):
    try:
        return max(0, min(10, int(float(fb.get("score", 0)))))
    except (TypeError, ValueError):
        return 0


def evaluate_text(round_key, question, answer, resume_text, language):
    focus = (
        "Judge technical correctness, depth and use of examples."
        if round_key == "technical"
        else "Judge clarity, honesty and structure (for example the STAR method: situation, task, action, result)."
    )
    prompt = f"""You are a strict but kind interviewer. Grade the candidate's answer. {focus}

Question: {question}

Candidate's answer: {answer}

Resume (for context): {resume_text[:1500]}

Return ONLY valid JSON (no markdown) in this exact format:
{{"score": <integer 0-10>, "strengths": "one short sentence", "improve": "one short sentence on what to improve", "better_answer": "a short model answer in 2-3 sentences"}}
Write the text fields in {language}. {LANG_RULES[language]}"""
    fb = parse_json(ask("You are an interview coach. Output only valid JSON.", prompt), "{", "}")
    return {
        "score": _score(fb),
        "strengths": str(fb.get("strengths", "")),
        "improve": str(fb.get("improve", "")),
        "better_answer": str(fb.get("better_answer", "")),
    }


def evaluate_code(item, user_code, approach, language, code_lang):
    prompt = f"""You are a coding interviewer reviewing a {code_lang} solution. You cannot run it, so read it carefully
and mentally trace it on the example and on edge cases.

Problem: {item['title']}
{item['question']}
Example: {item.get('example', '')}

Candidate's code:
{user_code}

Candidate's explanation of the approach: {approach or '(not given)'}

Scoring guide: correctness 6 points, time/space complexity 2 points, code clarity 2 points.

Return ONLY valid JSON (no markdown, no code) in this exact format:
{{"score": <integer 0-10>, "verdict": "Correct" or "Partially correct" or "Incorrect", "complexity": "Time O(...), Space O(...)", "strengths": "one short sentence", "improve": "one short sentence", "better_answer": "the optimal approach in 2-3 sentences, no code"}}
Write the text fields in {language}. {LANG_RULES[language]}"""
    fb = parse_json(ask("You are a careful code reviewer. Output only valid JSON.", prompt, 2000), "{", "}")
    return {
        "score": _score(fb),
        "verdict": str(fb.get("verdict", "")),
        "complexity": str(fb.get("complexity", "")),
        "strengths": str(fb.get("strengths", "")),
        "improve": str(fb.get("improve", "")),
        "better_answer": str(fb.get("better_answer", "")),
    }


def speak(text, lang_code):
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang=lang_code).write_to_fp(buf)
        return buf.getvalue()
    except Exception:
        return None


def show_feedback(r):
    if r.get("verdict"):
        st.write(f"**Verdict:** {r['verdict']}")
    if r.get("complexity"):
        st.write(f"**Complexity:** {r['complexity']}")
    if r["strengths"]:
        st.success(f"👍 {r['strengths']}")
    if r["improve"]:
        st.warning(f"🔧 {r['improve']}")
    if r["better_answer"]:
        st.info(f"💡 Better approach: {r['better_answer']}")


# one-time message when a new round starts
if st.session_state.mi_toast:
    st.toast(st.session_state.mi_toast)
    st.session_state.mi_toast = None

# ---------------- 1. Setup screen ----------------
if not st.session_state.mi_items:
    resume_file = st.file_uploader("Upload your resume", type=["pdf", "docx", "txt"])
    role = voice_or_text(
        "Job role you are interviewing for (optional)", key="mi_role_input",
        placeholder="e.g. Python Developer, Data Analyst",
    )

    st.markdown("**Choose your rounds**")
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        use_tech = st.checkbox("🛠️ Round: Technical", value=True)
        n_tech = st.slider("Technical questions", 2, 5, 3) if use_tech else 0
    with rc2:
        use_code = st.checkbox("💻 Round: Coding", value=True)
        n_code = st.slider("Coding problems", 1, 2, 1) if use_code else 0
    with rc3:
        use_hr = st.checkbox("🤝 Round: HR / Behavioural", value=True)
        n_hr = st.slider("HR questions", 2, 4, 2) if use_hr else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        language = st.selectbox("Interview language", ["English", "Tamil"])
    with c2:
        code_lang = st.selectbox("Coding language", list(CODE_LANGS.keys()))
    with c3:
        st.write("")
        read_aloud = st.checkbox("🔊 Read questions aloud", value=True)

    if st.button("Start Interview"):
        chosen = {"technical": n_tech if use_tech else 0, "coding": n_code if use_code else 0, "hr": n_hr if use_hr else 0}
        if not resume_file:
            st.warning("Please upload your resume first.")
        elif not any(chosen.values()):
            st.warning("Please choose at least one round.")
        else:
            try:
                with st.spinner("Reading your resume..."):
                    resume_text = read_resume(resume_file)
                if not resume_text or not resume_text.strip():
                    st.error("I couldn't read any text from this resume. Try a different file.")
                else:
                    items, round_keys = [], []
                    for rk in ROUND_ORDER:
                        if chosen[rk]:
                            with st.spinner(f"Preparing Round: {ROUNDS[rk][0]}..."):
                                round_items = generate_round(rk, resume_text, role, chosen[rk], language, code_lang)
                            if round_items:
                                items += round_items
                                round_keys.append(rk)
                    if not items:
                        st.error("Couldn't prepare the interview. Please try again.")
                    else:
                        reset_interview()
                        st.session_state.mi_items = items
                        st.session_state.mi_round_keys = round_keys
                        st.session_state.mi_resume_text = resume_text
                        st.session_state.mi_role = role or ""
                        st.session_state.mi_language = language
                        st.session_state.mi_code_lang = code_lang
                        st.session_state.mi_read_aloud = read_aloud
                        st.rerun()
            except Exception as e:
                st.error(f"Couldn't start the interview. Please try again. ({e})")

# ---------------- 3. Result screen ----------------
elif st.session_state.mi_done:
    results = st.session_state.mi_results
    keys = st.session_state.mi_round_keys
    total_score = sum(r["score"] for r in results)
    max_score = 10 * len(results)
    pct = round(100 * total_score / max_score) if max_score else 0

    # save for the Progress Dashboard (only once per interview)
    if not st.session_state.mi_logged:
        log_progress("interview", total_score, max_score, topic=st.session_state.mi_role or "General")
        st.session_state.mi_logged = True

    st.markdown(f"""
    <div class="score-card">
        <div class="score-num">{total_score}/{max_score}</div>
        <div class="score-label">OVERALL INTERVIEW SCORE &nbsp;•&nbsp; {pct}%</div>
    </div>
    """, unsafe_allow_html=True)

    # score of each round
    by_round = {}
    for r in results:
        by_round.setdefault(r["round_key"], []).append(r)
    shown = [k for k in keys if k in by_round]
    if shown:
        cols = st.columns(len(shown))
        for col, rk in zip(cols, shown):
            rs = by_round[rk]
            col.metric(f"{ROUNDS[rk][1]} {ROUNDS[rk][0]}", f"{sum(x['score'] for x in rs)}/{10 * len(rs)}")

    if pct >= 80:
        st.balloons()
        st.success("Excellent! You are interview ready 🔥")
    elif pct >= 55:
        st.info("Good attempt 👍 Work on the improvement points below.")
    else:
        st.warning("Keep practising 💪 Read the better approaches and try again.")

    weakest = sorted(results, key=lambda r: r["score"])[:2]
    if weakest and any(r["improve"] for r in weakest):
        st.subheader("🎯 Focus on")
        for r in weakest:
            if r["improve"]:
                st.write(f"- {r['improve']}")

    st.subheader("📖 Review")
    for n, r in enumerate(results, 1):
        name, icon = ROUNDS[r["round_key"]]
        label = r["title"] if r["round_key"] == "coding" else r["question"]
        with st.expander(f"{icon} {name} · Q{n}: {label}  —  {r['score']}/10"):
            if r["round_key"] == "coding":
                st.markdown(r["question"])
                st.write("**Your code:**")
                st.code(r["answer"], language=CODE_LANGS.get(st.session_state.mi_code_lang, "python"))
                if r.get("approach"):
                    st.write(f"**Your explanation:** {r['approach']}")
            else:
                st.write(f"**Your answer:** {r['answer']}")
            show_feedback(r)

    st.caption("Your score is saved in the Progress Dashboard.")
    if st.button("🔄 New Interview"):
        reset_interview()
        st.rerun()

# ---------------- 2. Question screen ----------------
else:
    items = st.session_state.mi_items
    keys = st.session_state.mi_round_keys
    i = st.session_state.mi_idx
    item = items[i]
    rk = item["round_key"]
    name, icon = ROUNDS[rk]
    language = st.session_state.mi_language
    lang_code = LANG_CODES[language]
    code_lang = st.session_state.mi_code_lang

    round_idx = [j for j, it in enumerate(items) if it["round_key"] == rk]
    st.progress(i / len(items))
    st.markdown(
        f"<span class='round-badge'>Round {keys.index(rk) + 1} of {len(keys)} · {icon} {name}</span>"
        f"&nbsp; Question {round_idx.index(i) + 1} of {len(round_idx)}",
        unsafe_allow_html=True,
    )

    if item["type"] == "coding":
        st.markdown(f"### {item['title']}")
        st.markdown(f"<div class='q-card'>{item['question']}</div>", unsafe_allow_html=True)
        if item.get("example"):
            st.code(item["example"], language=None)
    else:
        st.markdown(f"<div class='q-card'>{item['question']}</div>", unsafe_allow_html=True)
        if st.session_state.mi_read_aloud:
            if i not in st.session_state.mi_audio:
                st.session_state.mi_audio[i] = speak(item["question"], lang_code)
            if st.session_state.mi_audio[i]:
                st.audio(st.session_state.mi_audio[i], format="audio/mp3")

    if not st.session_state.mi_submitted:
        if item["type"] == "coding":
            user_code = st.text_area(
                f"Your {code_lang} code", height=280, key=f"mi_code_{i}",
                placeholder=f"Write your {code_lang} solution here...",
            )
            approach = voice_or_text(
                "Explain your approach (optional, type it or use the mic)", key=f"mi_approach_{i}",
                height=100, language=lang_code,
            )
            st.caption("Coding answers are reviewed by AI. The code is not executed, so also check it yourself.")
            ready = bool((user_code or "").strip())
        else:
            answer = voice_or_text(
                "Your answer (type it, or use the mic and speak)", key=f"mi_answer_{i}",
                height=150, language=lang_code,
            )
            ready = bool((answer or "").strip())

        if st.button("Submit answer", disabled=not ready):
            try:
                with st.spinner("Evaluating your answer..."):
                    if item["type"] == "coding":
                        fb = evaluate_code(item, user_code.strip(), (approach or "").strip(), language, code_lang)
                        fb.update({"answer": user_code.strip(), "approach": (approach or "").strip(), "title": item["title"]})
                    else:
                        fb = evaluate_text(rk, item["question"], answer.strip(), st.session_state.mi_resume_text, language)
                        fb.update({"answer": answer.strip()})
                fb.update({"round_key": rk, "question": item["question"]})
                st.session_state.mi_results.append(fb)
                st.session_state.mi_submitted = True
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't evaluate this answer. Please click Submit again. ({e})")
    else:
        r = st.session_state.mi_results[-1]
        if item["type"] == "coding":
            st.write("**Your code:**")
            st.code(r["answer"], language=CODE_LANGS.get(code_lang, "python"))
        else:
            st.write(f"**Your answer:** {r['answer']}")
        st.metric("Score for this answer", f"{r['score']}/10")
        show_feedback(r)

        label = "Next ➡️" if i + 1 < len(items) else "Finish 🏁"
        if st.button(label):
            st.session_state.mi_submitted = False
            if i + 1 < len(items):
                nxt = items[i + 1]
                if nxt["round_key"] != rk:
                    n_name, n_icon = ROUNDS[nxt["round_key"]]
                    st.session_state.mi_toast = f"Starting Round {keys.index(nxt['round_key']) + 1}: {n_icon} {n_name}"
                st.session_state.mi_idx += 1
            else:
                st.session_state.mi_done = True
            st.rerun()