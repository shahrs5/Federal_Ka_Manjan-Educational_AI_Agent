# Federal Ka Manjan - Educational AI Agent

A RAG-powered AI tutor for FBISE Class 9 & 10 students. Supports Physics, Chemistry, Biology, Computer Science, and English with multi-language responses (English, Urdu, Roman Urdu).

## Features

- **RAG Pipeline** — Retrieval-Augmented Generation grounded in your course notes
- **Query Rewriting** — Fixes typos and resolves follow-up references ("explain it") into self-contained queries before retrieval
- **Chapter Routing** — Automatically routes questions to relevant chapters using LLM + metadata
- **Chat Memory** — 10-message session history; the LLM uses prior turns to maintain context
- **Fallback to History** — If retrieval returns no chunks, the LLM answers from conversation history instead of bailing out
- **Multi-language** — English, Urdu, and Roman Urdu responses
- **Source Citations** — Shows which chapters were used and their relevance scores
- **Web UI** — Single-page dark-themed chat interface

## Architecture

```
User input + chat history
        │
        ▼
┌─────────────────────┐
│  Query Rewriter     │  gpt-oss-20b — fixes typos, resolves follow-ups
│  (last 4 history    │  using history context. Output is a self-contained
│   messages)         │  retrieval query.
└────────┬────────────┘
         │ rewritten query
         ▼
┌─────────────────────┐
│  Chapter Router     │  LLM picks primary + secondary chapters
│  (subject metadata) │  from subject_metadata using the rewritten query
└────────┬────────────┘
         │ chapter scope
         ▼
┌─────────────────────┐
│  RAG Retriever      │  Embeds rewritten query, vector search
│  (Supabase)         │  scoped to routed chapters
└────────┬────────────┘
         │ chunks (or empty)
         ▼
┌─────────────────────┐
│  QA Agent           │  gpt-oss-120b. Receives ORIGINAL user query
│  (full history +    │  + history + chunks. If no chunks, answers
│   chunks or none)   │  from history alone.
└────────┬────────────┘
         ▼
   Answer + Sources
```

## Setup

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/Federal_Ka_Manjan-Educational_AI_Agent.git
cd Federal_Ka_Manjan-Educational_AI_Agent

# Using uv (recommended)
uv sync

# Or using pip
# python -m venv .venv
# .venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
# pip install -r pyproject.toml
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
GROQ_API_KEY=your-groq-api-key

# LLM models (via Groq)
GROQ_MODEL=openai/gpt-oss-120b          # main answer model
GROQ_MODEL_FAST=openai/gpt-oss-20b      # query rewriter (low token usage)

# Embeddings — use gemini (requires GEMINI_API_KEY) or a local model
GEMINI_API_KEY=your-gemini-api-key
EMBEDDING_MODEL=gemini                   # or: sentence-transformers/all-mpnet-base-v2
```

### 3. Ingest Notes

Process all notes for a class into the vector database:

```bash
# All subjects for Class 9
uv scripts/ingest_all_subjects.py --class-level 9 --subjects all

# All subjects for Class 10
uv scripts/ingest_all_subjects.py --class-level 10 --subjects all

# Specific subjects only
uv scripts/ingest_all_subjects.py --class-level 9 --subjects Physics Chemistry
```

## Running the App

```bash
uvicorn src.api.main:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

## API

| Endpoint  | Method | Description        |
| --------- | ------ | ------------------ |
| `/`       | GET    | Chat UI            |
| `/health` | GET    | Health check       |
| `/chat`   | POST   | Process a question |

### Chat API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Newton'\''s second law?",
    "class_level": 9,
    "subject": "Physics",
    "language": "en",
    "history": [
      {"role": "user",      "content": "What is Newton'\''s first law?"},
      {"role": "assistant", "content": "Newton'\''s first law states..."}
    ]
  }'
```

**Response:**

```json
{
  "answer": "Newton's second law states that...",
  "explanation": "...",
  "sources": [
    { "chapter": 3, "title": "Dynamics", "snippet": "...", "relevance": 0.89 }
  ],
  "confidence": 0.85,
  "chapter_used": 3
}
```

## Configuration

| Variable               | Description                             | Default                   |
| ---------------------- | --------------------------------------- | ------------------------- |
| `SUPABASE_URL`         | Supabase project URL                    | Required                  |
| `SUPABASE_KEY`         | Supabase anon key                       | Required                  |
| `GROQ_API_KEY`         | Groq API key for LLM                    | Required                  |
| `GROQ_MODEL`           | Groq model name                         | `llama-3.3-70b-versatile` |
| `GEMINI_API_KEY`       | Gemini API key for embeddings           | Optional                  |
| `EMBEDDING_MODEL`      | `gemini` or sentence-transformers model | `gemini`                  |
| `CHUNK_SIZE`           | Text chunk size for RAG                 | `500`                     |
| `MAX_RAG_RESULTS`      | Max chunks to retrieve                  | `5`                       |
| `SIMILARITY_THRESHOLD` | Min similarity for retrieval            | `0.5`                     |

## Project Structure

```
├── src/
│   ├── config.py                      # Pydantic settings from .env
│   ├── agents/
│   │   ├── qa_agent.py                # Main orchestrator: rewrite → route → retrieve → answer
│   │   ├── chapter_router.py          # LLM routes queries to chapters via subject_metadata
│   │   └── rag_retriever.py           # Vector similarity search (Supabase RPC)
│   ├── api/
│   │   ├── main.py                    # FastAPI app, lifespan init, /chat endpoint
│   │   ├── models.py                  # Pydantic request/response models (incl. chat history)
│   │   └── templates/
│   │       └── index.html             # Chat UI (single file, vanilla JS)
│   ├── ingestion/
│   │   ├── pipeline.py                # Full pipeline: docx → extract → chunk → embed → upload
│   │   ├── docx_extractor.py          # Structured text extraction from .docx
│   │   ├── text_chunker.py            # Splits documents into chunks
│   │   ├── embedding_generator.py     # Gemini or sentence-transformers (768-dim)
│   │   ├── supabase_loader.py         # Writes chunks + embeddings to Supabase
│   │   └── subject_metadata.py        # Chapter titles/topics. Keyed: SUBJECT_METADATA[class][subject]
│   └── services/
│       ├── groq_client.py             # Groq client factory
│       └── supabase_client.py         # Supabase client factory
├── scripts/
│   ├── ingest_all_subjects.py         # CLI: ingest notes for any class/subject combo
│   ├── ingest_physics_notes.py        # Legacy single-subject ingestion script
│   ├── setup_supabase.sql             # Supabase schema (chapters + document_chunks + RPC)
│   └── migrate_to_768_dims.sql        # Migration for 768-dim embeddings
├── Notes/
│   ├── Class 9/                       # Physics, Chemistry, Biology, Computer Science, English
│   └── Class 10/                      # Physics, Chemistry, Biology (English & CS coming soon)
├── requirements.txt
├── .env.example
└── .env
```

## What's Available

| Class | Physics | Chemistry | Biology | Computer Science | English |
|-------|---------|-----------|---------|------------------|---------|
| 9     | All chapters | All chapters | All chapters | Ch 1, 2, 3, 5 | All chapters |
| 10    | 7 chapters | 7 chapters | 11 chapters | — | — |

## API Keys

- **Groq** — https://console.groq.com/keys (free tier available)
- **Gemini** — https://ai.google.dev/gemini-api/docs (free tier: 1500 req/min)
- **Supabase** — https://supabase.com (free tier available)

## License

MIT
