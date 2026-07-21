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
);

CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(id),
    feedback INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
);
