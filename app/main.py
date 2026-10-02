"""Compatibility ASGI entry point.

The canonical FastAPI application is defined in the repository-root main.py.
This wrapper preserves the legacy `uvicorn app.main:app` import path without
maintaining a second application implementation.
"""

from main import app

__all__ = ["app"]
