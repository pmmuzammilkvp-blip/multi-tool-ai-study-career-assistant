import io
import json
import os
import re
import time

import streamlit as st
from dotenv import load_dotenv
from groq import Groq, RateLimitError
from gtts import gTTS

from shared import search_knowledge_base, log_tool_use
from ui import inject_theme, hero, card, stat_tile, stepper, flashcard, mindmap

load_dotenv()

st.set_page_config(page_title="Study Pack", page_icon="🎁", layout="wide")
inject_theme()

hero("Study Pack", "One click. Your AI agent builds a summary, mind map, flashcards, quiz and audio.", "🎁")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "qwen/qwen3.8-27b"
SYSTEM = "You are a study assistant. Reply with valid JSON only, no markdown, no extra text."
STEPS = [("📝", "Summary"), ("🧠", "Mind map"), ("🃏", "Flashcards"), ("❓", "Quiz"), ("🎧", "Audio")]


# ---------------- helpers ----------------
def retry_seconds(err):
    m = re.search(r"try again in (?:(\d+)m)?\s*([\d.]+)s", str(err))
    return 30.0 if not m else int(m.group(1) or 0) * 60 + float(m.group(2))


def ask(prompt, max_tokens, on_wait):
    """One Groq call. If the free-tier limit is hit, wait and retry automatically."""
    for attempt in range(4):
        try:
            r = groq_client.chat.completions.create(
                model=MODEL, max_tokens=max_tokens, temperature=0.3,
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
            )
            text = r.choices[0].message.content or ""
            return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        except RateLimitError as e:
            wait = retry_seconds(e) + 1
            if attempt == 3 or wait > 70:
                raise
            on_wait(int(wait))
            time.sleep(wait)


def parse_json(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = text.replace("```json", "").replace("```", "").strip()
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise ValueError("model returned no JSON: " + text[:120])
    text = text[min(starts):]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # cut-off JSON: trim back until it can be closed
    for cut in range(len(text), 0, -1):
        chunk = text[:cut].rstrip().rstrip(",")
        stack, in_str, skip = [], False, False
        for ch in chunk:
            if in_str:
                if skip:
                    skip = False
                elif ch == "\\":
                    skip = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]" and stack:
                stack.pop()
        if in_str:
            continue
        try:
            return json.loads(chunk + "".join(reversed(stack)))
        except json.JSONDecodeError:
            continue
    raise ValueError("could not read model output")


def build_pack(topic, status_slot, steps_slot, note):
    # 1. Context: uploaded documents if available, otherwise general knowledge
    context, used_docs = "", False
    try:
        chunks, _ = search_knowledge_base(topic, n_results=5)
        if chunks:
            context, used_docs = "\n\n".join(chunks)[:3500], True
    except Exception:
        pass
    source = f"Use ONLY this content:\n{context}" if used_docs else "Use your general knowledge."
    log_tool_use("Document Search" if used_docs else "Direct Reply", f"Study Pack: {topic}")

    pack = {"topic": topic, "used_docs": used_docs}
    on_wait = lambda s: note.info(f"Free-tier rate limit reached. Resuming automatically in {s} seconds...")

    jobs = [
        ("summary", 500, f'Topic: {topic}\n{source}\nReturn JSON: {{"big_idea": "2 sentences", '
                         f'"key_points": ["4 short points"], "exam_focus": ["3 likely exam questions"]}}'),
        ("mindmap", 450, f'Topic: {topic}\n{source}\nReturn JSON: {{"center": "short title", "branches": '
                         f'[{{"title": "branch", "children": ["2 or 3 short items"]}}]}} with 4 or 5 branches.'),
        ("flashcards", 500, f'Topic: {topic}\n{source}\nReturn a JSON array of 6 flashcards: '
                            f'[{{"q": "question", "a": "short answer"}}]'),
        ("quiz", 700, f'Topic: {topic}\n{source}\nReturn a JSON array of 5 multiple-choice questions: '
                      f'[{{"question": "...", "options": ["4 option texts"], "answer": "exact text of the correct option", '
                      f'"explanation": "one line"}}]'),
    ]

    for i, (key, tokens, prompt) in enumerate(jobs):
        steps_slot.markdown(stepper(STEPS, i), unsafe_allow_html=True)
        note.empty()
        try:
            pack[key] = parse_json(ask(prompt, tokens, on_wait))
        except Exception as e:
            pack[key] = None
            pack.setdefault("errors", []).append(f"{STEPS[i][1]}: {e}")

    # 5. Audio (no Groq tokens needed)
    steps_slot.markdown(stepper(STEPS, 4), unsafe_allow_html=True)
    note.empty()
    s = pack.get("summary")
    if s:
        script = " ".join([s.get("big_idea", "")] + [str(p) for p in s.get("key_points", [])])[:1500]
        try:
            buf = io.BytesIO()
            gTTS(text=script, lang="en").write_to_fp(buf)
            pack["audio"] = buf.getvalue()
        except Exception as e:
            pack["audio"] = None
            pack.setdefault("errors", []).append(f"Audio: {e}")

    steps_slot.markdown(stepper(STEPS, len(STEPS)), unsafe_allow_html=True)
    return pack


def as_list(data):
    """Model sometimes wraps the list in a dict like {"questions": [...]}. Return a clean list of dicts."""
    if isinstance(data, dict):
        data = next((v for v in data.values() if isinstance(v, list)), [])
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict)]


# ---------------- input ----------------
topic = st.text_input("What do you want to study?", placeholder="e.g. Pandas DataFrame")
st.caption("Tip: upload your notes in Study Assistant first, and the pack is built from your own documents.")
go = st.button("✨ Create Study Pack")

if go and not topic.strip():
    st.warning("Please type a topic first, then click Create Study Pack.")

if go and topic.strip():
    steps_slot, note = st.empty(), st.empty()
    steps_slot.markdown(stepper(STEPS, 0), unsafe_allow_html=True)
    st.session_state["pack"] = build_pack(topic.strip(), None, steps_slot, note)
    note.empty()

# ---------------- results ----------------
pack = st.session_state.get("pack")
if pack:
    for err in pack.get("errors", []):
        st.warning(f"Could not build: {err}. Try again in a minute.")

    flash = as_list(pack.get("flashcards"))
    quiz = as_list(pack.get("quiz"))
    cols = st.columns(4)
    tiles = [("Your documents" if pack["used_docs"] else "General knowledge", "SOURCE"),
             (len(flash), "FLASHCARDS"), (len(quiz), "QUIZ QUESTIONS"),
             ("Ready" if pack.get("audio") else "-", "AUDIO")]
    for col, (n, l) in zip(cols, tiles):
        col.markdown(stat_tile(n, l), unsafe_allow_html=True)
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    t1, t2, t3, t4, t5 = st.tabs(["📝 Summary", "🧠 Mind Map", "🃏 Flashcards", "❓ Quiz", "🎧 Audio"])

    with t1:
        s = pack.get("summary")
        if isinstance(s, dict):
            a, b, c = st.columns(3)
            a.markdown(card("Big idea", s.get("big_idea", ""), "💡"), unsafe_allow_html=True)
            b.markdown(card("Key points", "", "🔑", s.get("key_points", [])), unsafe_allow_html=True)
            c.markdown(card("Exam focus", "", "🎯", s.get("exam_focus", [])), unsafe_allow_html=True)

    with t2:
        m = pack.get("mindmap")
        if isinstance(m, dict):
            branches = [b for b in m.get("branches", []) if isinstance(b, dict)]
            st.markdown(mindmap(m.get("center", pack["topic"]), branches), unsafe_allow_html=True)

    with t3:
        grid = st.columns(2)
        for i, c in enumerate(flash):
            grid[i % 2].markdown(flashcard(c.get("q", ""), c.get("a", "")), unsafe_allow_html=True)

    with t4:
        for i, q in enumerate(quiz):
            st.markdown(f"**Q{i + 1}. {q.get('question', '')}**")
            pick = st.radio("Choose one", q.get("options", []), index=None, key=f"pack_q{i}", label_visibility="collapsed")
            if pick:
                if pick.strip().lower() == str(q.get("answer", "")).strip().lower():
                    st.success("Correct!")
                else:
                    st.error(f"Wrong. Correct answer: {q.get('answer', '')}")
                if q.get("explanation"):
                    st.info(q["explanation"])
            st.divider()

    with t5:
        if pack.get("audio"):
            st.audio(pack["audio"], format="audio/mp3")
            st.download_button("⬇️ Download MP3", pack["audio"], file_name="study_pack.mp3", mime="audio/mpeg")
        else:
            st.info("Audio was not generated.")