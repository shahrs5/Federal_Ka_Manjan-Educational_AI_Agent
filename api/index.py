"""
Vercel entrypoint — re-exports the FastAPI app from src.api.main.
"""
from src.api.main import app  # noqa: F401
