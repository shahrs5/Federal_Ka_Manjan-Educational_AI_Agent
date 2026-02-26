"""Authentication dependencies for FastAPI."""
from fastapi import Request, HTTPException, Depends
from ..services.supabase_client import get_supabase_admin_client


def get_access_token(request: Request) -> str:
    """Extract access token from cookie."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token


def verify_jwt(token: str) -> dict:
    """Verify a Supabase JWT by calling the Supabase admin API."""
    try:
        client = get_supabase_admin_client()
        user = client.auth.get_user(token)
        # Build a payload dict matching what routes expect
        u = user.user
        return {
            "sub": str(u.id),
            "email": u.email,
            "app_metadata": u.app_metadata or {},
            "user_metadata": u.user_metadata or {},
        }
    except Exception as e:
        print(f"[AUTH] Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(request: Request) -> dict:
    """FastAPI dependency: returns user info or raises 401."""
    token = get_access_token(request)
    return verify_jwt(token)


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """FastAPI dependency: requires admin role in app_metadata."""
    app_metadata = user.get("app_metadata", {})
    if app_metadata.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
