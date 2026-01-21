-- =============================================================================
-- Supabase Schema for RAG Pipeline
-- Run this in your Supabase SQL Editor
-- =============================================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- Table 1: chapters - Chapter metadata for routing
-- =============================================================================
CREATE TABLE IF NOT EXISTS chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_level INTEGER NOT NULL CHECK (class_level IN (9, 10, 11)),
    subject VARCHAR(100) NOT NULL,
    chapter_number INTEGER NOT NULL,
    chapter_title VARCHAR(500) NOT NULL,
    chapter_description TEXT,
    topics JSONB DEFAULT '[]',
    source_file VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(class_level, subject, chapter_number)
);

-- =============================================================================
-- Table 2: document_chunks - The main RAG table with embeddings
-- =============================================================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,

    -- Content
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,

    -- Embedding (768 dimensions for Gemini text-embedding-004)
    embedding vector(768),

    -- Metadata for filtering and display
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_chapter_chunk UNIQUE(chapter_id, chunk_index)
);

-- =============================================================================
-- Indexes for performance
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_chunks_chapter_id ON document_chunks(chapter_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_chapters_class_subject ON chapters(class_level, subject);

-- =============================================================================
-- Function to update updated_at timestamp
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for chapters table
DROP TRIGGER IF EXISTS update_chapters_updated_at ON chapters;
CREATE TRIGGER update_chapters_updated_at
    BEFORE UPDATE ON chapters
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- RPC Function: search_chunks - Vector similarity search
-- =============================================================================
DROP FUNCTION IF EXISTS search_chunks;

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

-- =============================================================================
-- Seed data: Physics Class 9 chapter metadata
-- =============================================================================
INSERT INTO chapters (class_level, subject, chapter_number, chapter_title, chapter_description, topics, source_file) VALUES
(9, 'Physics', 1, 'Physical Quantities and Measurement',
 'Covers fundamental and derived quantities, SI units, scientific notation, measuring instruments like vernier caliper and screw gauge, and significant figures.',
 '["physical quantities", "SI units", "measurement", "vernier caliper", "screw gauge", "significant figures", "scientific notation"]',
 'Chapter 1 - Notes (Final 1).docx'),

(9, 'Physics', 2, 'Kinematics',
 'Describes motion in one dimension including displacement, velocity, acceleration, equations of motion, and graphical analysis of motion.',
 '["motion", "displacement", "velocity", "acceleration", "equations of motion", "distance-time graph", "velocity-time graph", "free fall"]',
 'Chapter 2 - Notes (Final 1).docx'),

(9, 'Physics', 3, 'Dynamics',
 'Covers Newtons laws of motion, force, momentum, friction, and circular motion.',
 '["force", "Newton laws", "momentum", "friction", "inertia", "action reaction", "circular motion", "centripetal force"]',
 'Chapter 3 - Notes (Final 1).docx'),

(9, 'Physics', 4, 'Turning Effect of Forces',
 'Explains torque, equilibrium, center of gravity, couples, and stability.',
 '["torque", "moment of force", "equilibrium", "center of gravity", "couple", "stability", "lever", "principle of moments"]',
 'Chapter 4 - Notes (Final 1).docx'),

(9, 'Physics', 5, 'Gravitation',
 'Covers gravitational force, Newtons law of gravitation, mass and weight, gravitational field strength.',
 '["gravitation", "gravity", "mass", "weight", "gravitational field", "Newton law of gravitation", "g value", "satellites"]',
 'Chapter 5 - Notes (Final 1).docx'),

(9, 'Physics', 6, 'Work and Energy',
 'Describes work, energy, power, kinetic and potential energy, and energy conservation.',
 '["work", "energy", "power", "kinetic energy", "potential energy", "conservation of energy", "efficiency", "joule"]',
 'Chapter 6 - Notes (Final 1).docx'),

(9, 'Physics', 7, 'Properties of Matter',
 'Covers states of matter, density, pressure, atmospheric pressure, and Archimedes principle.',
 '["density", "pressure", "atmospheric pressure", "Archimedes principle", "buoyancy", "Pascal law", "states of matter"]',
 'Chapter 7 - Notes (Final 1).docx'),

(9, 'Physics', 8, 'Thermal Properties of Matter',
 'Explains temperature, heat, thermal expansion, specific heat capacity, and heat transfer.',
 '["temperature", "heat", "thermal expansion", "specific heat", "latent heat", "conduction", "convection", "radiation"]',
 'Chapter 8 - Notes (Final 1).docx'),

(9, 'Physics', 9, 'Transfer of Heat',
 'Covers conduction, convection, radiation, and applications of heat transfer.',
 '["conduction", "convection", "radiation", "thermal conductivity", "insulation", "greenhouse effect", "thermos flask"]',
 'Chapter 9 - Notes (Final 1).docx')
ON CONFLICT (class_level, subject, chapter_number) DO UPDATE SET
    chapter_title = EXCLUDED.chapter_title,
    chapter_description = EXCLUDED.chapter_description,
    topics = EXCLUDED.topics,
    source_file = EXCLUDED.source_file;
