"""
Chat interaction logger — writes each chat to the Supabase `chat_logs` table.
"""
import json
import traceback

from .supabase_client import get_supabase_client


def log_chat(row: dict) -> None:
    """Insert a row into chat_logs."""
    try:
        # Ensure all values are JSON-serializable (convert any numpy/custom floats)
        clean_row = {}
        for k, v in row.items():
            if isinstance(v, float):
                clean_row[k] = float(v)
            elif isinstance(v, int) and not isinstance(v, bool):
                clean_row[k] = int(v)
            else:
                clean_row[k] = v

        supabase = get_supabase_client()
        result = supabase.table("chat_logs").insert(clean_row).execute()
        print(f"[chat_logger] OK — id={result.data[0]['id'] if result.data else '?'}")
    except Exception as e:
        print(f"[chat_logger] FAILED: {e}")
        traceback.print_exc()


def build_chat_log_row(
    *,
    user_id: str,
    user_email: str,
    class_level: int,
    subject: str,
    language: str,
    original_query: str,
    chat_history: list,
    response,
) -> dict:
    """Build the row dict from the response object. Safe to call from any thread."""
    routing = response.routing_info
    routing_info = {
        "primary_chapter": routing.primary_chapter,
        "secondary_chapters": routing.secondary_chapters,
        "confidence": routing.confidence,
        "reasoning": routing.reasoning,
        "topics_identified": routing.topics_identified,
    }

    return {
        "user_id": user_id,
        "user_email": user_email,
        "class_level": class_level,
        "subject": subject,
        "language": language,
        "original_query": original_query,
        "revised_query": response.revised_query or None,
        "chat_history": chat_history,
        "agent_used": response.agent_used or None,
        "math_intent": response.math_intent or None,
        "routing_info": routing_info,
        "sources": response.sources,
        "answer": response.answer,
        "explanation": response.explanation,
        "confidence": response.confidence,
        "chapter_used": response.chapter_used,
    }
