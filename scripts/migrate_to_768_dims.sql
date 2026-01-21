-- =============================================================================
-- Migration: Update schema from 384 to 768 dimensions for Gemini embeddings
-- Run this in Supabase SQL Editor
-- =============================================================================

-- Step 1: Drop existing indexes and function (they reference 384 dims)
DROP INDEX IF EXISTS idx_chunks_embedding;
DROP FUNCTION IF EXISTS search_chunks;

-- Step 2: Clear existing chunks (embeddings are incompatible)
DELETE FROM document_chunks;

-- Step 3: Alter the embedding column to 768 dimensions
ALTER TABLE document_chunks
ALTER COLUMN embedding TYPE vector(768);

-- Step 4: Recreate the HNSW index for 768 dimensions
CREATE INDEX idx_chunks_embedding
ON document_chunks
USING hnsw (embedding vector_cosine_ops);

-- Step 5: Recreate the search function for 768 dimensions
CREATE OR REPLACE FUNCTION search_chunks(
    query_embedding vector(768),
    match_count int DEFAULT 5,
    filter_class int DEFAULT NULL,
    filter_subject text DEFAULT NULL,
    filter_chapters int[] DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    chunk_text TEXT,
    chapter_number INT,
    chapter_title VARCHAR(500),
    similarity FLOAT,
    metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id AS chunk_id,
        dc.chunk_text,
        c.chapter_number,
        c.chapter_title,
        (1 - (dc.embedding <=> query_embedding))::FLOAT AS similarity,
        dc.metadata
    FROM document_chunks dc
    JOIN chapters c ON dc.chapter_id = c.id
    WHERE
        (filter_class IS NULL OR c.class_level = filter_class)
        AND (filter_subject IS NULL OR c.subject = filter_subject)
        AND (filter_chapters IS NULL OR c.chapter_number = ANY(filter_chapters))
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Done! Now run the ingestion script to re-populate with Gemini embeddings.
