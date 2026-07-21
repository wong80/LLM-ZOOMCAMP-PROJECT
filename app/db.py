"""PostgreSQL operations for conversation and feedback persistence."""

import os
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "pydoc_assistant"),
        user=os.getenv("POSTGRES_USER", "user"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
    )


def init_db(conn=None):
    close = conn is None
    if conn is None:
        conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    response_time FLOAT NOT NULL,
                    relevance TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    eval_prompt_tokens INTEGER NOT NULL,
                    eval_completion_tokens INTEGER NOT NULL,
                    eval_total_tokens INTEGER NOT NULL,
                    openai_cost FLOAT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    conversation_id TEXT REFERENCES conversations(id),
                    feedback INTEGER NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
        conn.commit()
    finally:
        if close:
            conn.close()


def save_conversation(conn, conv: dict):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO conversations
               (id, question, answer, model_used, response_time, relevance,
                prompt_tokens, completion_tokens, total_tokens,
                eval_prompt_tokens, eval_completion_tokens, eval_total_tokens,
                openai_cost, timestamp)
               VALUES (%(id)s, %(question)s, %(answer)s, %(model_used)s,
                       %(response_time)s, %(relevance)s,
                       %(prompt_tokens)s, %(completion_tokens)s, %(total_tokens)s,
                       %(eval_prompt_tokens)s, %(eval_completion_tokens)s,
                       %(eval_total_tokens)s, %(openai_cost)s, %(timestamp)s)""",
            conv,
        )
    conn.commit()


def get_conversation(conn, conversation_id: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM conversations WHERE id = %s", (conversation_id,))
        row = cur.fetchone()
    if row is None:
        return None
    if hasattr(row, "keys"):
        return dict(row)
    COLUMNS = [
        "id", "question", "answer", "model_used", "response_time",
        "relevance", "prompt_tokens", "completion_tokens", "total_tokens",
        "eval_prompt_tokens", "eval_completion_tokens", "eval_total_tokens",
        "openai_cost", "timestamp",
    ]
    return dict(zip(COLUMNS, row))


def save_feedback(conn, conversation_id: str, feedback: int):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO feedback (conversation_id, feedback, timestamp) VALUES (%s, %s, %s)",
            (conversation_id, feedback, datetime.now(timezone.utc)),
        )
    conn.commit()


def get_feedback(conn, conversation_id: str) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT feedback FROM feedback WHERE conversation_id = %s ORDER BY timestamp DESC LIMIT 1",
            (conversation_id,),
        )
        row = cur.fetchone()
        return row[0] if row else None
