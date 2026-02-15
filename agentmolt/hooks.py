"""Pre/post request hooks and middleware."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("agentmolt.hooks")


def logging_hook_pre(method: str, path: str, data: Optional[Dict[str, Any]]) -> None:
    """Pre-hook that logs every outgoing request."""
    logger.info("AgentMolt request: %s %s", method, path)


def logging_hook_post(method: str, path: str, data: Optional[Dict[str, Any]], response: Dict[str, Any]) -> None:
    """Post-hook that logs every response."""
    logger.info("AgentMolt response: %s %s -> %d keys", method, path, len(response))


def timing_hook() -> tuple:
    """Returns a (pre, post) hook pair that logs request duration.

    Usage::

        pre, post = timing_hook()
        am.add_hook("pre", pre)
        am.add_hook("post", post)
    """
    state: Dict[str, float] = {}

    def pre(method: str, path: str, data: Any) -> None:
        state["start"] = time.time()

    def post(method: str, path: str, data: Any, response: Any) -> None:
        elapsed = time.time() - state.get("start", time.time())
        logger.info("AgentMolt %s %s took %.3fs", method, path, elapsed)

    return pre, post
