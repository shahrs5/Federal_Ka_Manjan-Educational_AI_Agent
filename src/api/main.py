"""
FastAPI application for the RAG chatbot.

Run with:
    uvicorn src.api.main:app --reload --port 8000
"""
from dotenv import load_dotenv
load_dotenv()  # Load .env before other imports

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from contextlib import asynccontextmanager

from ..config import settings
from ..services.groq_client import get_groq_client
from ..services.supabase_client import get_supabase_client
from ..ingestion.embedding_generator import EmbeddingGenerator
from ..agents.chapter_router import ChapterRouterAgent
from ..agents.rag_retriever import RAGRetriever
from ..agents.qa_agent import QAAgent
from .models import ChatRequest, ChatResponse, SourceInfo, HealthResponse


# Global instances (initialized on startup)
qa_agent: QAAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize RAG pipeline on startup."""
    global qa_agent

    # Validate settings
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY must be set in .env")
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

    # Initialize clients
    groq_client = get_groq_client()
    supabase_client = get_supabase_client()
    embedder = EmbeddingGenerator(settings.embedding_model)

    # Initialize agents
    router = ChapterRouterAgent(groq_client, model=settings.groq_model, debug=False)
    retriever = RAGRetriever(
        supabase_client=supabase_client,
        embedding_generator=embedder,
        top_k=settings.max_rag_results,
        similarity_threshold=settings.similarity_threshold,
        debug=False,
    )
    qa_agent = QAAgent(
        llm_client=groq_client,
        router=router,
        retriever=retriever,
        model=settings.groq_model,
        model_fast=settings.groq_model_fast,
    )

    print("RAG pipeline initialized successfully!")
    yield
    # Cleanup (if needed)
    print("Shutting down...")


app = FastAPI(
    title="Federal Ka Manjan - Educational AI Agent",
    description="RAG-powered chatbot for Class 9 & 10 Physics",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the chat UI."""
    html_path = Path(__file__).parent / "templates" / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(
        content="<h1>Federal Ka Manjan</h1><p>Chat UI not found. API is running.</p>"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok", message="RAG chatbot is running")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a student's question and return an answer.

    - **query**: The question to ask
    - **class_level**: 9 or 10
    - **subject**: Currently supports "Physics"
    - **language**: "en" (English), "ur" (Urdu), or "ur-roman" (Roman Urdu)
    """
    if qa_agent is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")

    try:
        response = qa_agent.answer(
            query=request.query,
            class_level=request.class_level,
            subject=request.subject,
            language=request.language,
        )

        sources = [
            SourceInfo(
                chapter=src["chapter"],
                title=src["title"],
                snippet=src["snippet"],
                relevance=src["relevance"],
            )
            for src in response.sources
        ]

        return ChatResponse(
            answer=response.answer,
            explanation=response.explanation,
            sources=sources,
            confidence=response.confidence,
            chapter_used=response.chapter_used,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
