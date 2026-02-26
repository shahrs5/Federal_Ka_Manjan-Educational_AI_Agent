"""
Supabase client wrapper.
"""
from supabase import create_client, Client
from functools import lru_cache
from ..config import settings


@lru_cache()
def get_supabase_client() -> Client:
    """Get cached Supabase client instance."""
    return create_client(settings.supabase_url, settings.supabase_key)


@lru_cache()
def get_supabase_admin_client() -> Client:
    """Get cached Supabase admin client using service role key."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
