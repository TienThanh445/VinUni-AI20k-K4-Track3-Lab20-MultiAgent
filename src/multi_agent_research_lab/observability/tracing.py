import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Any

from multi_agent_research_lab.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def setup_tracing(settings: Settings | None = None) -> None:
    """Configure external tracing providers (LangSmith, Langfuse) if keys are provided."""
    s = settings or get_settings()

    # LangSmith tracing configuration
    if s.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = s.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = s.langsmith_project
        logger.info(f"LangSmith tracing enabled for project: {s.langsmith_project}")

    # Langfuse tracing configuration
    if s.langfuse_public_key and s.langfuse_secret_key:
        os.environ["LANGFUSE_PUBLIC_KEY"] = s.langfuse_public_key
        os.environ["LANGFUSE_SECRET_KEY"] = s.langfuse_secret_key
        os.environ["LANGFUSE_HOST"] = s.langfuse_host
        logger.info(f"Langfuse tracing enabled for host: {s.langfuse_host}")


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Context manager for tracing an execution span with latency and attribute tracking."""
    started = perf_counter()
    span: dict[str, Any] = {
        "name": name,
        "attributes": attributes or {},
        "status": "running",
        "duration_seconds": None,
    }
    try:
        yield span
        span["status"] = "ok"
    except Exception as exc:
        span["status"] = "error"
        span["error"] = str(exc)
        raise
    finally:
        span["duration_seconds"] = perf_counter() - started
