# FBISE Learning Assistant - Implementation Plan (Simplified)

## Overview

**Architecture:** 2-Agent System with SPOAR Loop
**LLM:** Google Gemini
**Backend:** FastAPI + PostgreSQL + pgvector
**Pattern:** Orchestrator (SPOAR) + Subject Agent (RAG)

---

## Architecture

### Two-Agent System

#### 1. Orchestrator Agent (SPOAR Loop)
- **Purpose:** Validate completeness and iterate until satisfied
- **Pattern:** **S**ense → **P**lan → **A**ct → **O**bserve → **R**eflect
- **Iterations:**
  - **Iteration 1:** Get resources (notes/videos)
  - **Iteration 2:** Get explanations/questions
  - **Iteration 3+:** Add conclusion if needed
- **Stopping:** When reflection determines answer is complete

#### 2. Subject Agent (RAG + Tools)
- **Purpose:** Execute tasks using knowledge base
- **Knowledge:** Subject-specific (Physics, Chemistry, Biology, Maths, English, Comp Sci) + Class (9, 10)
- **Tools:**
  1. **Resource Fetcher:** Return Drive/YouTube links
  2. **RAG Search:** Semantic search over knowledge chunks
  3. **Explanation Generator:** Create explanations using retrieved context
  4. **Question Maker:** Generate practice questions

### Flow

```
Student Query (with session: class + subject)
       ↓
Orchestrator (SPOAR Loop)
   ├─ SENSE: What's needed? Context?
   ├─ PLAN: Resources? Explanation? Questions?
   ├─ ACT: Call Subject Agent with tools
   │     ↓
   │  Subject Agent:
   │   ├─ Check: Resource request only?
   │   │   YES → Fetch resources from DB
   │   │   NO  → Simplify query + RAG search
   │   ├─ RAG: Retrieve relevant chunks
   │   └─ Generate: Explanation OR Questions
   │     ↓
   ├─ OBSERVE: What came back?
   └─ REFLECT: Complete? Clear? Need more?
       ↓
   Loop or Return Final Answer
```

---

## Project Structure

```
base-agent.py                    # SPOAR implementation (exists)

src/
├── main.py                      # FastAPI entry
├── config.py                    # Config (pydantic-settings)
│
├── api/
│   ├── routes/
│   │   ├── chat.py              # POST /api/chat
│   │   ├── session.py           # POST /api/session/start
│   │   ├── feedback.py          # POST /api/feedback
│   │   └── health.py            # GET /health
│   ├── models/
│   │   ├── request.py
│   │   ├── response.py
│   │   └── feedback.py
│   └── middleware/
│       ├── error_handler.py
│       └── logging_middleware.py
│
├── agents/
│   ├── orchestrator.py          # Orchestrator (SPOAR)
│   ├── subject_agent.py         # Subject Agent (RAG + tools)
│   └── tools.py                 # Tool definitions
│
├── services/
│   ├── gemini_client.py         # Gemini API wrapper
│   ├── embedding_service.py     # Sentence transformers
│   ├── rag_service.py           # Vector search (pgvector)
│   └── resource_service.py      # Fetch Drive/YouTube links
│
├── database/
│   ├── connection.py            # SQLAlchemy
│   ├── models.py                # ORM models
│   └── repositories/
│       ├── knowledge_base.py
│       └── session_repo.py
│
└── utils/
    ├── logger.py
    └── prompt_templates.py

migrations/                       # Alembic
tests/
scripts/
```

---

## Phase 1: Setup & Dependencies

### 1. Create requirements.txt
```txt
# Web
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0

# Database
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
alembic==1.13.1
pgvector==0.2.4

# AI
google-generativeai==0.3.1
sentence-transformers==2.3.1

# Utils
python-dotenv==1.0.0
tenacity==8.2.3
```

### 2. Create .env.example
```env
APP_ENV=development
API_PORT=8000

DATABASE_URL=postgresql://user:pass@localhost:5432/fbise_db

GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-pro

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

MAX_ORCHESTRATOR_ITERATIONS=3
```

### 3. Create pytest.ini
```ini
[pytest]
testpaths = tests
asyncio_mode = auto
addopts = -v --cov=src
```

---

## Phase 2: Database Schema

### Tables

#### 1. sessions
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    class_level INTEGER NOT NULL CHECK (class_level IN (9, 10)),
    subject VARCHAR(100) NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. knowledge_chunks (RAG)
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_level INTEGER NOT NULL,
    subject VARCHAR(100) NOT NULL,
    chapter INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_knowledge_embedding ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_knowledge_class_subject_chapter ON knowledge_chunks(class_level, subject, chapter);
```

#### 3. resources
```sql
CREATE TABLE resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_level INTEGER NOT NULL,
    subject VARCHAR(100) NOT NULL,
    chapter INTEGER,
    resource_type VARCHAR(50) CHECK (resource_type IN ('notes', 'video')),
    title VARCHAR(500),
    url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. chat_logs
```sql
CREATE TABLE chat_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    user_message TEXT NOT NULL,
    agent_response JSONB NOT NULL,
    iterations INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### 5. feedback
```sql
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_log_id UUID REFERENCES chat_logs(id),
    feedback_type VARCHAR(50),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## Phase 3: Core Services

### 1. Gemini Client (src/services/gemini_client.py)

```python
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate(
        self,
        prompt: str,
        system_instruction: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Generate text from Gemini"""
        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        response = self.model.generate_content(
            full_prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens
            }
        )
        return response.text

    async def generate_json(self, prompt: str, system_instruction: str = None) -> dict:
        """Generate structured JSON output"""
        response = await self.generate(
            prompt,
            system_instruction=f"{system_instruction}\n\nRespond with ONLY valid JSON."
        )
        import json
        return json.loads(response)
```

### 2. RAG Service (src/services/rag_service.py)

```python
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from sqlalchemy import text

class RAGService:
    def __init__(self, db_session, embedding_model: str):
        self.db = db_session
        self.model = SentenceTransformer(embedding_model)

    async def search(
        self,
        query: str,
        class_level: int,
        subject: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Semantic search using pgvector"""
        # Generate query embedding
        query_embedding = self.model.encode(query).tolist()

        # Vector similarity search
        sql = text("""
            SELECT
                chunk_text,
                chapter,
                metadata,
                1 - (embedding <=> :query_embedding) AS similarity
            FROM knowledge_chunks
            WHERE class_level = :class_level AND subject = :subject
            ORDER BY embedding <=> :query_embedding
            LIMIT :top_k
        """)

        result = await self.db.execute(
            sql,
            {
                "query_embedding": str(query_embedding),
                "class_level": class_level,
                "subject": subject,
                "top_k": top_k
            }
        )

        return [
            {
                "text": row.chunk_text,
                "chapter": row.chapter,
                "similarity": row.similarity,
                "metadata": row.metadata
            }
            for row in result
        ]
```

### 3. Resource Service (src/services/resource_service.py)

```python
class ResourceService:
    def __init__(self, db_session):
        self.db = db_session

    async def get_resources(
        self,
        class_level: int,
        subject: str,
        chapter: int = None
    ) -> List[Dict[str, str]]:
        """Fetch Drive/YouTube links"""
        from sqlalchemy import select
        from src.database.models import Resource

        query = select(Resource).where(
            Resource.class_level == class_level,
            Resource.subject == subject
        )

        if chapter:
            query = query.where(Resource.chapter == chapter)

        result = await self.db.execute(query)
        resources = result.scalars().all()

        return [
            {
                "title": r.title,
                "url": r.url,
                "type": r.resource_type
            }
            for r in resources
        ]
```

---

## Phase 4: Agent Implementation

### 1. Orchestrator Agent (src/agents/orchestrator.py)

**Extends base-agent.py SPOAR pattern**

```python
from base_agent import SimpleAgent  # Import from base-agent.py
from src.agents.subject_agent import SubjectAgent
from src.services.gemini_client import GeminiClient

class OrchestratorAgent(SimpleAgent):
    """
    Orchestrator using SPOAR loop to validate completeness.

    Iterations:
    1. Get resources
    2. Get explanation/questions
    3+ Add conclusion if needed
    """

    def __init__(self, gemini_client: GeminiClient, subject_agent: SubjectAgent):
        super().__init__()
        self.llm_client = gemini_client  # Override LLM
        self.subject_agent = subject_agent
        self.context = {}

    async def run(self, user_query: str, session_context: dict, max_iterations: int = 3):
        """
        Run SPOAR loop.

        session_context: {class_level, subject, language}
        """
        self.context = {
            "goal": "Answer student query comprehensively",
            "query": user_query,
            "session": session_context,
            "iteration": 0,
            "accumulated_response": {}
        }

        for iteration in range(1, max_iterations + 1):
            self.context["iteration"] = iteration

            # SENSE
            context = self._sense(self.context)

            # PLAN
            plan = await self._plan(context)

            # Check if complete
            if plan["action"] == "COMPLETE":
                return plan["answer"]

            # ACT (call Subject Agent)
            result = await self._act(plan)

            # OBSERVE
            observation = self._observe(plan, result)

            # REFLECT
            reflection = await self._reflect(context, observation)

            # Update context
            self.context["last_action"] = plan
            self.context["last_result"] = result
            self.context["last_reflection"] = reflection

        return self.context.get("accumulated_response", "Max iterations reached")

    async def _act(self, plan: dict):
        """Call Subject Agent with planned action"""
        action = plan.get("action")

        if action == "GET_RESOURCES":
            return await self.subject_agent.fetch_resources(
                self.context["session"]["class_level"],
                self.context["session"]["subject"],
                chapter=plan.get("chapter")
            )

        elif action == "GET_EXPLANATION":
            return await self.subject_agent.generate_explanation(
                query=self.context["query"],
                class_level=self.context["session"]["class_level"],
                subject=self.context["session"]["subject"]
            )

        elif action == "GET_QUESTIONS":
            return await self.subject_agent.generate_questions(
                topic=plan.get("topic"),
                class_level=self.context["session"]["class_level"],
                subject=self.context["session"]["subject"]
            )

        else:
            return "Unknown action"
```

### 2. Subject Agent (src/agents/subject_agent.py)

```python
from src.services.rag_service import RAGService
from src.services.resource_service import ResourceService
from src.services.gemini_client import GeminiClient

class SubjectAgent:
    """
    Main worker agent with RAG + tools.
    """

    def __init__(
        self,
        gemini_client: GeminiClient,
        rag_service: RAGService,
        resource_service: ResourceService
    ):
        self.gemini = gemini_client
        self.rag = rag_service
        self.resources = resource_service

    async def fetch_resources(
        self,
        class_level: int,
        subject: str,
        chapter: int = None
    ):
        """Tool: Fetch Drive/YouTube links"""
        return await self.resources.get_resources(class_level, subject, chapter)

    async def generate_explanation(
        self,
        query: str,
        class_level: int,
        subject: str
    ):
        """Tool: Generate explanation using RAG"""
        # 1. Simplify query
        simplified = await self._simplify_query(query)

        # 2. RAG search
        chunks = await self.rag.search(simplified, class_level, subject, top_k=5)

        # 3. Generate explanation
        context = "\n\n".join([chunk["text"] for chunk in chunks])

        prompt = f"""You are a tutor for Class {class_level} {subject}.

Context from textbook:
{context}

Student Question: {query}

Provide a clear, simple explanation in 2-3 paragraphs. Use examples where helpful."""

        explanation = await self.gemini.generate(prompt, temperature=0.7)

        return {
            "explanation": explanation,
            "sources": [{"chapter": c["chapter"]} for c in chunks]
        }

    async def generate_questions(
        self,
        topic: str,
        class_level: int,
        subject: str,
        num_questions: int = 3
    ):
        """Tool: Generate practice questions"""
        # RAG search for topic
        chunks = await self.rag.search(topic, class_level, subject, top_k=3)
        context = "\n\n".join([chunk["text"] for chunk in chunks])

        prompt = f"""You are creating practice questions for Class {class_level} {subject}.

Topic: {topic}
Reference material:
{context}

Generate {num_questions} practice questions:
- Mix conceptual and numerical
- Match Class {class_level} difficulty
- Provide answers

Format as JSON:
{{"questions": [{{"q": "...", "a": "..."}}]}}"""

        response = await self.gemini.generate_json(prompt)
        return response["questions"]

    async def _simplify_query(self, query: str) -> str:
        """Extract key concepts from query"""
        prompt = f"""Extract the main topic/concept from this student question in 5-10 words:

Question: {query}

Topic:"""
        return await self.gemini.generate(prompt, temperature=0.3, max_tokens=50)
```

---

## Phase 5: API Endpoints

### POST /api/session/start
```python
class SessionRequest(BaseModel):
    class_level: int = Field(..., ge=9, le=10)
    subject: str
    language: str = "en"

@router.post("/session/start")
async def start_session(request: SessionRequest, db: AsyncSession = Depends(get_db)):
    # Create session in DB
    session_id = str(uuid.uuid4())
    # ... save to DB
    return {"session_id": session_id}
```

### POST /api/chat
```python
class ChatRequest(BaseModel):
    session_id: str
    message: str

@router.post("/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    # 1. Get session context
    session = await get_session(request.session_id)

    # 2. Run orchestrator
    orchestrator = OrchestratorAgent(gemini_client, subject_agent)
    response = await orchestrator.run(
        user_query=request.message,
        session_context={
            "class_level": session.class_level,
            "subject": session.subject,
            "language": session.language
        }
    )

    # 3. Log to DB
    # ... log chat

    return {"response": response}
```

---

## Phase 6: Testing

### test_orchestrator.py
```python
@pytest.mark.asyncio
async def test_orchestrator_complete_response(mock_gemini, mock_subject_agent):
    orchestrator = OrchestratorAgent(mock_gemini, mock_subject_agent)

    response = await orchestrator.run(
        user_query="Explain Newton's laws",
        session_context={"class_level": 10, "subject": "physics", "language": "en"}
    )

    assert "Newton" in response
    assert orchestrator.context["iteration"] <= 3
```

### test_subject_agent.py
```python
@pytest.mark.asyncio
async def test_subject_agent_explanation(mock_gemini, mock_rag):
    agent = SubjectAgent(mock_gemini, mock_rag, mock_resources)

    result = await agent.generate_explanation(
        query="What is force?",
        class_level=10,
        subject="physics"
    )

    assert "explanation" in result
    assert len(result["sources"]) > 0
```

---

## Implementation Sequence

### Week 1: Foundation
1. Set up project structure
2. Install dependencies (requirements.txt)
3. Configure .env
4. Set up PostgreSQL + pgvector
5. Create Alembic migrations
6. Run migrations

### Week 2: Core Services
7. Implement Gemini client
8. Implement Embedding service
9. Implement RAG service
10. Implement Resource service
11. Test services individually

### Week 3: Agents
12. Adapt base-agent.py to Orchestrator
13. Implement Subject Agent
14. Implement agent tools
15. Test agents with mocks

### Week 4: API
16. Implement FastAPI app
17. Implement /session/start endpoint
18. Implement /chat endpoint
19. Implement middleware
20. Integration tests

### Week 5: Knowledge Base
21. Prepare knowledge base data
22. Generate embeddings
23. Seed database
24. Test RAG search quality

### Week 6: Testing & Refinement
25. End-to-end testing
26. Performance optimization
27. Add logging/monitoring
28. Documentation

---

## Success Criteria

- [ ] Orchestrator completes in ≤3 iterations
- [ ] RAG retrieves relevant chunks (>0.7 similarity)
- [ ] Responses are accurate and helpful
- [ ] API latency <3 seconds
- [ ] Resources fetched correctly
- [ ] Tests passing with >80% coverage

---

## Next Steps

1. **Add more subjects:** Expand beyond initial subjects
2. **Multilingual:** Full Urdu support
3. **WhatsApp integration:** Add WhatsApp channel
4. **Analytics:** Track usage and quality metrics
5. **Web UI:** Build student-facing frontend
