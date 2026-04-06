"""
FastAPI app for the Support Ticket Triage Environment.
"""
import sys
import os

# Ensure the env root is on sys.path for absolute imports
_env_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _env_root not in sys.path:
    sys.path.insert(0, _env_root)

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError("openenv-core is required: pip install openenv-core") from e

from models import TriageAction, TicketObservation
from server.support_triage_env_environment import SupportTriageEnvironment

app = create_app(
    SupportTriageEnvironment,
    TriageAction,
    TicketObservation,
    env_name="support_triage_env",
    max_concurrent_envs=4,
)


def main(host: str = "0.0.0.0", port: int = 8000):
    """Entry point for uv run / python -m execution."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
