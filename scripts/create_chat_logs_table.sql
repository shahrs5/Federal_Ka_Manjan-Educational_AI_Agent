-- Chat Logs table for logging all chat interactions
-- Run this in the Supabase SQL Editor

CREATE TABLE chat_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now(),
    user_id TEXT NOT NULL,
    user_email TEXT NOT NULL,
    class_level INT NOT NULL,
    subject TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    original_query TEXT NOT NULL,
    revised_query TEXT,
    chat_history JSONB DEFAULT '[]',
    agent_used TEXT,
    math_intent TEXT,
    routing_info JSONB,
    sources JSONB DEFAULT '[]',
    answer TEXT,
    explanation TEXT,
    confidence FLOAT,
    chapter_used INT
);

CREATE INDEX idx_chat_logs_user_id ON chat_logs(user_id);
CREATE INDEX idx_chat_logs_created_at ON chat_logs(created_at DESC);
