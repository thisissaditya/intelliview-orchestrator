CREATE TABLE IF NOT EXISTS subscribers (
    webhook_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    secret_ref TEXT NOT NULL,
    active BOOLEAN DEFAULT 1,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS interview_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    candidate_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    assigned_node VARCHAR(255),
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    risk_score FLOAT,
    integrity_score FLOAT,
    fused_signal JSON,
    video_analysis JSON,
    audio_analysis JSON,
    evaluation_analysis JSON,
    llm_usage JSON,
    questions_asked JSON,
    answers_provided JSON,
    feedback_generated JSON,
    overall_score FLOAT,
    template_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);



ALTER TABLE interview_sessions ADD COLUMN IF NOT EXISTS integrity_score FLOAT;
ALTER TABLE interview_sessions ADD COLUMN IF NOT EXISTS fused_signal JSON;