import os
import opik
from dotenv import load_dotenv

load_dotenv()

def setup_opik():
    """
    Initialize Opik configuration from environment variables.
    """
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
