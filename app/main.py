"""PyDoc Assistant — Streamlit UI for RAG-powered Q&A over Python docs."""

import os
import sys
import uuid
from datetime import datetime, timezone

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

import app.db as db
from app.rag import rag


def render_answer(result: dict) -> str:
    html = f"<p>{result['answer']}</p>"
    if result.get("citations"):
        html += "<p><strong>Sources:</strong></p><ul>"
        for url in result["citations"]:
            html += f'<li><a href="{url}" target="_blank">{url}</a></li>'
        html += "</ul>"
    return html


def save_feedback(conversation_id: str, feedback: int):
    conn = db.get_connection()
    try:
        db.save_feedback(conn, conversation_id, feedback)
    finally:
        conn.close()


def main():
    st.set_page_config(page_title="PyDoc Assistant", page_icon="🐍")
    st.title("🐍 PyDoc Assistant")

    if "history" not in st.session_state:
        st.session_state.history = []
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
    if "last_answer" not in st.session_state:
        st.session_state.last_answer = None

    st.selectbox("Library", ["FastAPI"], index=0)

    question = st.text_input("Ask a question about FastAPI:")

    col1, col2 = st.columns([1, 5])
    with col1:
        asked = st.button("Ask")
    with col2:
        st.write("")

    if asked:
        if not question or not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Searching docs and generating answer..."):
                result = rag(question)
            st.session_state.last_answer = result

            conv_id = str(uuid.uuid4())
            st.session_state.conversation_id = conv_id
            st.session_state.history.append({"question": question, "answer": result["answer"]})

            eval_tokens = result.get("eval_tokens") or {}
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
                "eval_prompt_tokens": eval_tokens.get("prompt_tokens", 0),
                "eval_completion_tokens": eval_tokens.get("completion_tokens", 0),
                "eval_total_tokens": eval_tokens.get("total_tokens", 0),
                "openai_cost": result.get("cost", 0),
                "timestamp": datetime.now(timezone.utc),
            }
            try:
                conn = db.get_connection()
                db.save_conversation(conn, conv)
                conn.close()
            except Exception as e:
                st.warning(f"Could not save conversation: {e}")

    if st.session_state.conversation_id and st.session_state.last_answer:
        ans = st.session_state.last_answer
        st.markdown(render_answer(ans), unsafe_allow_html=True)
        st.caption(f"{ans.get('response_time', 0):.1f}s | {ans.get('model', '')} | {ans.get('relevance', '')}")
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
            st.session_state.history = []
            st.rerun()
        for item in reversed(st.session_state.history[-50:]):
            q = item["question"]
            st.markdown(f"- {q[:60]}{'...' if len(q) > 60 else ''} ✓")


if __name__ == "__main__":
    main()
