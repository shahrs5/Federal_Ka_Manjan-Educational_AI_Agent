"""
FastAPI application for the RAG chatbot.

Run with:
    uvicorn src.api.main:app --reload --port 8000
"""
import asyncio
from dotenv import load_dotenv
load_dotenv()  # Load .env before other imports

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from contextlib import asynccontextmanager

from ..config import settings
from ..services.groq_client import get_groq_client
from ..services.supabase_client import get_supabase_client, get_supabase_admin_client
from ..services.opik_setup import setup_opik
from ..services.chat_logger import log_chat, build_chat_log_row
from ..ingestion.embedding_generator import EmbeddingGenerator
from ..agents.chapter_router import ChapterRouterAgent
from ..agents.rag_retriever import RAGRetriever
from ..agents.qa_agent import QAAgent
from ..agents.math_formula_agent import MathFormulaAgent
from ..agents.math_solving_agent import MathSolvingAgent
from ..agents.math_orchestrator import MathOrchestrator
from .models import (
    ChatRequest, ChatResponse, SourceInfo, HealthResponse,
    LoginRequest, SetPasswordRequest, FirstTimeCheckRequest,
    FirstTimeSetPasswordRequest, InviteUserRequest, BulkInviteRequest, UserInfo,
)
from .auth import get_current_user, require_admin, verify_jwt


# Global instances (initialized on startup)
qa_agent: QAAgent = None
math_orchestrator: MathOrchestrator = None

TEMPLATES = Path(__file__).parent / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize RAG pipeline on startup."""
    global qa_agent, math_orchestrator

    # Validate settings
    if not settings.groq_key_list:
        raise RuntimeError("GROQ_API_KEYS (or GROQ_API_KEY) must be set in .env")
    if not settings.gemini_key_list:
        raise RuntimeError("GEMINI_API_KEYS (or GEMINI_API_KEY) must be set in .env")
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

    # Initialize clients
    setup_opik()
    groq_client = get_groq_client()
    supabase_client = get_supabase_client()
    embedder = EmbeddingGenerator(settings.embedding_model, api_keys=settings.gemini_key_list)

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

    # Math agents (share the same router, retriever, and groq_client)
    math_formula = MathFormulaAgent(
        llm_client=groq_client,
        router=router,
        retriever=retriever,
        model=settings.groq_model,
        model_fast=settings.groq_model_fast,
    )
    math_solver = MathSolvingAgent(
        llm_client=groq_client,
        model=settings.groq_model,
    )
    math_orchestrator = MathOrchestrator(
        formula_agent=math_formula,
        solving_agent=math_solver,
        llm_client=groq_client,
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


# ── Public Routes ────────────────────────────────────────────────

@app.get("/logo.png")
async def serve_logo():
    logo_path = Path(__file__).parent.parent / "logo.png"
    return FileResponse(logo_path, media_type="image/png")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the login page. Redirect to / if already authenticated."""
    token = request.cookies.get("access_token")
    if token:
        try:
            verify_jwt(token)
            return RedirectResponse(url="/", status_code=302)
        except Exception:
            pass
    return HTMLResponse(content=(TEMPLATES / "login.html").read_text(encoding="utf-8"))


@app.get("/set-password", response_class=HTMLResponse)
async def set_password_page():
    """Serve the set-password page (first-time login and password reset)."""
    return HTMLResponse(content=(TEMPLATES / "set_password.html").read_text(encoding="utf-8"))


@app.get("/auth/config")
async def auth_config():
    """Public endpoint returning Supabase URL and anon key for client-side auth."""
    return {"supabase_url": settings.supabase_url, "supabase_key": settings.supabase_key}


@app.post("/auth/login")
async def auth_login(req: LoginRequest):
    """Receive tokens from Supabase client-side auth and set HttpOnly cookies."""
    payload = verify_jwt(req.access_token)

    response = JSONResponse(content={"ok": True, "email": payload.get("email")})

    cookie_params = {
        "key": "access_token",
        "value": req.access_token,
        "httponly": True,
        "samesite": "lax",
        "secure": settings.app_env != "development",
        "path": "/",
    }
    if req.remember_me:
        cookie_params["max_age"] = 30 * 24 * 3600  # 30 days

    response.set_cookie(**cookie_params)

    # Also store refresh token for future token renewal
    refresh_params = {
        **cookie_params,
        "key": "refresh_token",
        "value": req.refresh_token,
    }
    response.set_cookie(**refresh_params)

    return response


@app.post("/auth/set-password")
async def auth_set_password(req: SetPasswordRequest, user: dict = Depends(get_current_user)):
    """Set password for first-time login users, then clear the must_reset flag."""
    client = get_supabase_admin_client()
    user_id = user.get("sub")
    try:
        client.auth.admin.update_user_by_id(
            user_id,
            {
                "password": req.password,
                "app_metadata": {"must_reset_password": False},
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.post("/auth/first-time-check")
async def first_time_check(req: FirstTimeCheckRequest):
    """Check if an email belongs to a user who has never logged in."""
    client = get_supabase_admin_client()
    try:
        users = client.auth.admin.list_users()
        for u in users:
            if u.email and u.email.lower() == req.email.lower():
                if u.last_sign_in_at is None:
                    return {"ok": True, "exists": True, "first_time": True}
                else:
                    return {"ok": True, "exists": True, "first_time": False}
        return {"ok": True, "exists": False, "first_time": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/first-time-setup")
async def first_time_setup(req: FirstTimeSetPasswordRequest):
    """Set password for a first-time user. Only works if they have never logged in."""
    client = get_supabase_admin_client()
    try:
        users = client.auth.admin.list_users()
        target = None
        for u in users:
            if u.email and u.email.lower() == req.email.lower():
                target = u
                break

        if not target:
            raise HTTPException(status_code=404, detail="No account found with this email")

        if target.last_sign_in_at is not None:
            raise HTTPException(status_code=400, detail="This account has already been set up. Use login instead.")

        client.auth.admin.update_user_by_id(
            str(target.id),
            {"password": req.password},
        )
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/logout")
async def auth_logout():
    """Clear auth cookies."""
    response = JSONResponse(content={"ok": True})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response


@app.post("/auth/refresh")
async def auth_refresh(request: Request):
    """Refresh an expired access token using the refresh token."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    admin_client = get_supabase_admin_client()
    try:
        res = admin_client.auth.refresh_session(refresh_token)
        session = res.session
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Refresh failed: {str(e)}")

    response = JSONResponse(content={"ok": True})
    cookie_params = {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.app_env != "development",
        "path": "/",
    }
    response.set_cookie(key="access_token", value=session.access_token, **cookie_params)
    response.set_cookie(key="refresh_token", value=session.refresh_token, **cookie_params)
    return response


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok", message="RAG chatbot is running")


# ── Protected Routes ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the chat UI (requires authentication)."""
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=302)
    try:
        verify_jwt(token)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    html_path = TEMPLATES / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(
        content="<h1>Federal Ka Manjan</h1><p>Chat UI not found. API is running.</p>"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: dict = Depends(get_current_user)):
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
        history = [{"role": m.role, "content": m.content} for m in request.history]

        if request.subject == "Math" and math_orchestrator is not None:
            response = await asyncio.to_thread(
                math_orchestrator.answer,
                query=request.query,
                class_level=request.class_level,
                language=request.language,
                history=history,
            )
        else:
            response = await asyncio.to_thread(
                qa_agent.answer,
                query=request.query,
                class_level=request.class_level,
                subject=request.subject,
                language=request.language,
                history=history,
            )
            if not response.agent_used:
                response.agent_used = "qa"

        sources = [
            SourceInfo(
                chapter=src["chapter"],
                title=src["title"],
                snippet=src["snippet"],
                relevance=src["relevance"],
            )
            for src in response.sources
        ]

        # Log chat interaction (run in thread to avoid blocking)
        try:
            chat_log_row = build_chat_log_row(
                user_id=user.get("sub", ""),
                user_email=user.get("email", ""),
                class_level=request.class_level,
                subject=request.subject,
                language=request.language,
                original_query=request.query,
                chat_history=history,
                response=response,
            )
            await asyncio.to_thread(log_chat, chat_log_row)
        except Exception as log_err:
            print(f"[chat] logging failed: {log_err}")

        return ChatResponse(
            answer=response.answer,
            explanation=response.explanation,
            sources=sources,
            confidence=response.confidence,
            chapter_used=response.chapter_used,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


# ── Admin Routes ─────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Serve the admin panel (requires admin role)."""
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=302)
    try:
        payload = verify_jwt(token)
        if payload.get("app_metadata", {}).get("role") != "admin":
            return RedirectResponse(url="/", status_code=302)
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    return HTMLResponse(content=(TEMPLATES / "admin.html").read_text(encoding="utf-8"))


@app.get("/api/admin/users")
async def list_users(admin: dict = Depends(require_admin)):
    """List all users (admin only)."""
    client = get_supabase_admin_client()
    response = client.auth.admin.list_users()
    users = [
        UserInfo(
            id=str(u.id),
            email=u.email or "",
            created_at=str(u.created_at) if u.created_at else "",
            last_sign_in=str(u.last_sign_in_at) if u.last_sign_in_at else None,
            role=(u.app_metadata or {}).get("role", "user"),
        )
        for u in response
    ]
    return users


@app.post("/api/admin/invite")
async def invite_user(req: InviteUserRequest, admin: dict = Depends(require_admin)):
    """Create a user by email (admin only). User sets their own password via First Time setup."""
    import secrets
    client = get_supabase_admin_client()
    try:
        client.auth.admin.create_user(
            {
                "email": req.email,
                "password": secrets.token_urlsafe(32),
                "email_confirm": True,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "email": req.email}


@app.post("/api/admin/bulk-invite")
async def bulk_invite(req: BulkInviteRequest, admin: dict = Depends(require_admin)):
    """Create multiple users by comma-separated emails (admin only)."""
    import secrets
    client = get_supabase_admin_client()
    emails = [e.strip() for e in req.emails.split(",") if e.strip()]
    results = []
    for email in emails:
        try:
            client.auth.admin.create_user(
                {
                    "email": email,
                    "password": secrets.token_urlsafe(32),
                    "email_confirm": True,
                }
            )
            results.append({"email": email, "status": "added"})
        except Exception as e:
            results.append({"email": email, "status": "error", "detail": str(e)})
    return {"results": results}


@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    """Delete a user by ID (admin only)."""
    client = get_supabase_admin_client()
    try:
        client.auth.admin.delete_user(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
