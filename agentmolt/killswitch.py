"""Kill switch — background polling for kill signals."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional

logger = logging.getLogger("agentmolt.killswitch")


class KillSwitch:
    """Polls the AgentMolt API for kill signals in a background thread.

    Usage::

        am = AgentMolt(api_key="am_...")
        ks = KillSwitch(am, agent_id="agent-123", poll_interval=5)
        ks.start()
        # ... do work ...
        ks.stop()

    When a kill signal is detected the default handler raises ``SystemExit``.
    Override with a custom callback via ``on_kill``.
    """

    def __init__(
        self,
        client: Any,
        agent_id: str,
        poll_interval: float = 5.0,
        on_kill: Optional[Callable[[], None]] = None,
    ) -> None:
        self.client = client
        self.agent_id = agent_id
        self.poll_interval = poll_interval
        self.on_kill = on_kill or self._default_kill
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @staticmethod
    def _default_kill() -> None:
        logger.critical("Kill signal received — raising SystemExit")
        raise SystemExit("AgentMolt kill signal received")

    def start(self) -> None:
        """Start background polling."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="agentmolt-killswitch")
        self._thread.start()
        logger.info("Kill switch polling started for agent %s", self.agent_id)

    def stop(self) -> None:
        """Stop background polling."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self.poll_interval + 1)
            self._thread = None

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                agent = self.client.get_agent(self.agent_id)
                status = getattr(agent, "status", None) or (agent.get("status") if isinstance(agent, dict) else None)
                if status in ("killed", "stopped"):
                    logger.warning("Agent %s status is %s — triggering kill", self.agent_id, status)
                    self.on_kill()
                    return
            except SystemExit:
                raise
            except Exception:
                logger.debug("Kill switch poll error", exc_info=True)
            self._stop_event.wait(self.poll_interval)
