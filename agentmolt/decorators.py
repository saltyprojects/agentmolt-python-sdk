"""Decorators for automatic monitoring."""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, Optional, TypeVar, cast

logger = logging.getLogger("agentmolt.decorators")

F = TypeVar("F", bound=Callable[..., Any])


def monitor(
    client: Any,
    agent_id: str,
    action: Optional[str] = None,
    target: str = "",
) -> Callable[[F], F]:
    """Decorator that auto-logs events and metrics for the wrapped function.

    Usage::

        am = AgentMolt(api_key="am_...")

        @monitor(am, agent_id="agent-123")
        def search(query: str) -> str:
            ...

    Logs a ``function_call`` event before execution and a metric with
    ``tool_calls=1`` after completion.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            act = action or fn.__name__
            try:
                client.log_event(agent_id, action=act, target=target, status="started")
            except Exception:
                logger.debug("Failed to log pre-event for %s", act, exc_info=True)

            start = time.time()
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                try:
                    client.log_event(agent_id, action=act, target=target, status="failed", metadata={"error": str(exc)})
                except Exception:
                    logger.debug("Failed to log failure event", exc_info=True)
                raise

            elapsed = time.time() - start
            try:
                client.log_event(agent_id, action=act, target=target, status="allowed", metadata={"duration_s": round(elapsed, 3)})
                client.log_metric(agent_id, tool_calls=1)
            except Exception:
                logger.debug("Failed to log post-event for %s", act, exc_info=True)

            return result

        return cast(F, wrapper)

    return decorator
