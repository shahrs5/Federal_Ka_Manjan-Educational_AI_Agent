# Federal Ka Manjan - Educational AI Agent

A RAG-powered AI tutor for Class 9 & 10 Physics students following the Federal Board curriculum in Pakistan.

## Features

- **RAG Pipeline**: Retrieval-Augmented Generation using your physics notes
- **Chapter Routing**: Automatically routes questions to relevant chapters
- **Multi-language Support**: English, Urdu, and Roman Urdu responses
- **Web UI**: Clean chat interface built with FastAPI
- **Source Citations**: Shows which chapters and sections were used to answer

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User      │────▶│  FastAPI Server  │────▶│  Chapter Router │
│  Question   │     │    /chat API     │     │   (Groq LLM)    │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                      │
                    ┌──────────────────┐              ▼
                    │    QA Agent      │◀────┌─────────────────┐
                    │   (Groq LLM)     │     │  RAG Retriever  │
                    └────────┬─────────┘     │   (Supabase)    │
                             │               └─────────────────┘
                             ▼
                    ┌──────────────────┐
                    │  Answer + Sources│
                    └──────────────────┘
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

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
GROQ_API_KEY=your-groq-api-key

# Recommended: Use Gemini for embeddings (free, no large downloads)
GEMINI_API_KEY=your-gemini-api-key
EMBEDDING_MODEL=gemini
```

### 3. Ingest Notes

Before using the chatbot, ingest your physics notes into the vector database:

```bash
uv run scripts/ingest_physics_notes.py
```

## Running the App

### Start the Server

```bash
uv run uvicorn src.api.main:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

### API Endpoints

| Endpoint  | Method | Description        |
| --------- | ------ | ------------------ |
| `/`       | GET    | Chat UI            |
| `/health` | GET    | Health check       |
| `/chat`   | POST   | Process a question |

### Chat API Example

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Newton'\''s second law of motion?",
    "class_level": 9,
    "subject": "Physics",
    "language": "en"
  }'
```

**Response:**

```json
{
  "answer": "Newton's second law states that...",
  "explanation": "",
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
│   ├── agents/
│   │   ├── chapter_router.py   # Routes questions to chapters
│   │   ├── qa_agent.py         # Main QA agent
│   │   └── rag_retriever.py    # Vector search retrieval
│   ├── api/
│   │   ├── main.py             # FastAPI application
│   │   ├── models.py           # Pydantic models
│   │   └── templates/
│   │       └── index.html      # Chat UI
│   ├── ingestion/
│   │   ├── docx_extractor.py   # Extract text from .docx
│   │   ├── embedding_generator.py  # Generate embeddings
│   │   ├── pipeline.py         # Ingestion pipeline
│   │   └── text_chunker.py     # Chunk text for RAG
│   ├── services/
│   │   ├── groq_client.py      # Groq LLM client
│   │   └── supabase_client.py  # Supabase vector store
│   └── config.py               # Settings management
├── scripts/
│   ├── ingest_physics_notes.py # Ingest notes into DB
│   └── test_rag_pipeline.py    # Test the RAG pipeline
├── Notes/                      # Physics notes (.docx files)
├── requirements.txt
└── .env.example
```

## API Keys

- **Groq**: https://console.groq.com/keys (free tier available)
- **Gemini**: https://makersuite.google.com/app/apikey (free tier: 1500 req/min)
- **Supabase**: https://supabase.com (free tier available)

## License

MIT
