"""PyDoc Assistant — Streamlit UI for RAG-powered Q&A over Python docs."""

import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure project root is importable when streamlit runs the script
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

import app.db as db
from app.rag import rag


def show_title() -> str:
    return "PyDoc Assistant"


def validate_question(question: str) -> tuple[bool, str]:
    if not question or not question.strip():
        return False, "Please enter a question."
    return True, ""


def handle_question(question: str) -> dict:
    result = rag(question)
    return result


def render_answer(result: dict) -> str:
    html = f"<p>{result['answer']}</p>"
    if result.get("citations"):
        html += "<p><strong>Sources:</strong></p><ul>"
        for url in result["citations"]:
            html += f'<li><a href="{url}" target="_blank">{url}</a></li>'
        html += "</ul>"
    return html


def render_metadata(result: dict) -> str:
    rt = result.get("response_time", 0)
    model = result.get("model", "")
    relevance = result.get("relevance", "")
    return f"{rt:.1f}s | {model} | {relevance}"


def get_library_selector() -> tuple[list[str], str]:
    return ["FastAPI"], "FastAPI"


def save_feedback(conversation_id: str, feedback: int):
    conn = db.get_connection()
    try:
        db.save_feedback(conn, conversation_id, feedback)
    finally:
        conn.close()


class SessionManager:
    def __init__(self, max_length: int = 50):
        self._history = []
        self._max_length = max_length

    def add_conversation(self, question: str, answer: str):
        self._history.append({"question": question, "answer": answer})
        if len(self._history) > self._max_length:
            self._history = self._history[-self._max_length:]

    def get_history(self) -> list[dict]:
        return list(self._history)

    def clear(self):
        self._history = []


def main():
    st.set_page_config(page_title=show_title(), page_icon="🐍")
    st.title(f"🐍 {show_title()}")

    if "session" not in st.session_state:
        st.session_state.session = SessionManager()
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
    if "last_answer" not in st.session_state:
        st.session_state.last_answer = None

    libs, default_lib = get_library_selector()
    st.selectbox("Library", libs, index=libs.index(default_lib))

    question = st.text_input("Ask a question about FastAPI:")

    col1, col2 = st.columns([1, 5])
    with col1:
        asked = st.button("Ask")
    with col2:
        st.write("")

    if asked:
        valid, msg = validate_question(question)
        if not valid:
            st.warning(msg)
        else:
            with st.spinner("Searching docs and generating answer..."):
                result = handle_question(question)
            st.session_state.last_answer = result

            conv_id = str(uuid.uuid4())
            st.session_state.conversation_id = conv_id
            st.session_state.session.add_conversation(question, result["answer"])

            conv = {
                "id": conv_id,
                "question": question,
                "answer": result["answer"],
                "model_used": result.get("model", ""),
                "response_time": result.get("response_time", 0),
                "relevance": result.get("relevance", ""),
                "prompt_tokens": result.get("prompt_tokens", 0),
                "completion_tokens": result.get("completion_tokens", 0),
                "total_tokens": result.get("total_tokens", 0),
                "eval_prompt_tokens": result.get("eval_tokens", {}).get("prompt_tokens", 0) if isinstance(result.get("eval_tokens"), dict) else 0,
                "eval_completion_tokens": result.get("eval_tokens", {}).get("completion_tokens", 0) if isinstance(result.get("eval_tokens"), dict) else 0,
                "eval_total_tokens": result.get("eval_tokens", {}).get("total_tokens", 0) if isinstance(result.get("eval_tokens"), dict) else 0,
                "openai_cost": result.get("cost", 0),
                "timestamp": datetime.now(timezone.utc),
            }
            try:
                conn = db.get_connection()
                db.save_conversation(conn, conv)
                conn.close()
            except Exception:
                pass

    # Render feedback buttons after the answer, outside the asked block
    if st.session_state.conversation_id and st.session_state.last_answer:
        st.markdown(render_answer(st.session_state.last_answer), unsafe_allow_html=True)
        st.caption(render_metadata(st.session_state.last_answer))
        cid = st.session_state.conversation_id
        fb_col1, fb_col2 = st.columns([1, 10])
        with fb_col1:
            if st.button("👍", key="thumbs_up"):
                try:
                    conn = db.get_connection()
                    db.save_feedback(conn, cid, 1)
                    conn.close()
                    st.success("Feedback saved!")
                except Exception as e:
                    st.error(f"Feedback failed: {e}")
        with fb_col2:
            if st.button("👎", key="thumbs_down"):
                try:
                    conn = db.get_connection()
                    db.save_feedback(conn, cid, -1)
                    conn.close()
                    st.success("Feedback saved!")
                except Exception as e:
                    st.error(f"Feedback failed: {e}")

    with st.sidebar:
        st.markdown("### Previous Questions")
        if st.button("Clear History"):
            st.session_state.session.clear()
            st.rerun()
        for item in reversed(st.session_state.session.get_history()):
            q = item["question"]
            st.markdown(f"- {q[:60]}{'...' if len(q) > 60 else ''} ✓")


if __name__ == "__main__":
    main()
