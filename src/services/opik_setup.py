import os
from dotenv import load_dotenv

load_dotenv()

try:
    import opik
    _HAS_OPIK = True
except ImportError:
    _HAS_OPIK = False


def _noop_decorator(fn):
    """No-op decorator when opik is not installed."""
    return fn


def get_track_decorator():
    """Return opik.track if available, otherwise a no-op."""
    if _HAS_OPIK:
        return opik.track
    return _noop_decorator


def setup_opik():
    """
    Initialize Opik configuration from environment variables.
    """
    if not _HAS_OPIK:
        print("Opik not installed. Tracing disabled.")
        return

    api_key = os.getenv("OPIK_API_KEY")
    workspace_name = os.getenv("OPIK_WORKSPACE_NAME", "shaheer-shahid")

    if api_key:
        opik.configure(
            api_key=api_key,
            workspace=workspace_name
        )
        print(f"Opik configured for workspace: {workspace_name}")
    else:
        print("Opik API Key not found. Tracing will be disabled or local only.")
