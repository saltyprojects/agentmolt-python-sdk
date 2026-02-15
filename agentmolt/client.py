"""AgentMolt Python SDK client."""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
import urllib.error
from typing import Any, Callable, Dict, List, Optional

from .exceptions import AgentMoltError, AuthenticationError, NotFoundError
from .models import Agent, Event, Metric, PolicyResult

logger = logging.getLogger("agentmolt")

DEFAULT_BASE_URL = "https://agentmolt.dev"
_MAX_RETRIES = 3
_BACKOFF_BASE = 0.5
_RETRYABLE_CODES = {429, 500, 502, 503, 504}


class AgentMolt:
    """Client for the AgentMolt API.

    Usage::

        from agentmolt import AgentMolt

        am = AgentMolt(api_key="am_...")
        agent = am.register_agent("my-agent", model="gpt-4")
        am.log_event(agent.id, action="tool_call", target="search_api")
        am.kill(agent.id)

    Environment variables ``AGENTMOLT_API_KEY`` and ``AGENTMOLT_BASE_URL``
    are read automatically when the corresponding argument is omitted.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self.api_key: str = api_key or os.environ.get("AGENTMOLT_API_KEY", "")
        if not self.api_key:
            raise AuthenticationError("api_key is required (pass it or set AGENTMOLT_API_KEY)")
        self.base_url: str = (base_url or os.environ.get("AGENTMOLT_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.max_retries = max_retries
        self._hooks: Dict[str, List[Callable[..., Any]]] = {"pre": [], "post": []}

    # -- context manager --

    def __enter__(self) -> "AgentMolt":
        return self

    def __exit__(self, *exc: Any) -> None:
        pass

    # -- hooks --

    def add_hook(self, stage: str, fn: Callable[..., Any]) -> None:
        """Register a pre or post request hook.

        ``stage`` must be ``'pre'`` or ``'post'``.
        Pre hooks receive ``(method, path, data)``.
        Post hooks receive ``(method, path, data, response)``.
        """
        if stage not in self._hooks:
            raise ValueError("stage must be 'pre' or 'post'")
        self._hooks[stage].append(fn)

    # -- internal --

    def _request(self, method: str, path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        for fn in self._hooks["pre"]:
            fn(method, path, data)

        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = json.dumps(data).encode() if data else None

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method=method)
                with urllib.request.urlopen(req) as resp:
                    result: Dict[str, Any] = json.loads(resp.read().decode())
                    for fn in self._hooks["post"]:
                        fn(method, path, data, result)
                    return result
            except urllib.error.HTTPError as e:
                resp_body = e.read().decode()
                try:
                    msg = json.loads(resp_body).get("error", resp_body)
                except json.JSONDecodeError:
                    msg = resp_body

                if e.code in _RETRYABLE_CODES and attempt < self.max_retries - 1:
                    wait = _BACKOFF_BASE * (2 ** attempt)
                    logger.warning("Retryable error %s on %s %s, retrying in %.1fs", e.code, method, path, wait)
                    time.sleep(wait)
                    last_exc = AgentMoltError(msg, status_code=e.code)
                    continue

                if e.code == 401:
                    raise AuthenticationError(msg, status_code=e.code)
                elif e.code == 404:
                    raise NotFoundError(msg, status_code=e.code)
                else:
                    raise AgentMoltError(msg, status_code=e.code)
            except urllib.error.URLError as e:
                if attempt < self.max_retries - 1:
                    wait = _BACKOFF_BASE * (2 ** attempt)
                    logger.warning("Connection error on %s %s, retrying in %.1fs", method, path, wait)
                    time.sleep(wait)
                    last_exc = AgentMoltError(f"Connection error: {e.reason}")
                    continue
                raise AgentMoltError(f"Connection error: {e.reason}")

        raise last_exc or AgentMoltError("Request failed after retries")

    # --- Agents ---

    def register_agent(self, name: str, model: str = "", metadata: Optional[Dict[str, Any]] = None) -> Agent:
        """Register a new agent. Returns an :class:`Agent`."""
        resp = self._request("POST", "/api/v1/agents/register", {
            "name": name,
            "model": model,
            "metadata": metadata or {},
        })
        return Agent.from_dict(resp)

    def list_agents(self) -> List[Agent]:
        """List all agents."""
        resp = self._request("GET", "/api/v1/agents")
        return [Agent.from_dict(a) for a in resp.get("agents", [])]

    def get_agent(self, agent_id: str) -> Agent:
        """Get agent details."""
        return Agent.from_dict(self._request("GET", f"/api/v1/agents/{agent_id}"))

    def update_status(self, agent_id: str, status: str) -> Agent:
        """Update agent status (idle, running, stopped, failed)."""
        return Agent.from_dict(self._request("POST", f"/api/v1/agents/{agent_id}/status", {"status": status}))

    def kill(self, agent_id: str) -> Dict[str, Any]:
        """Kill switch — immediately stop an agent."""
        return self._request("POST", f"/api/v1/agents/{agent_id}/kill")

    # --- Events ---

    def log_event(
        self,
        agent_id: str,
        action: str,
        target: str = "",
        status: str = "allowed",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Event:
        """Log an agent event."""
        resp = self._request("POST", "/api/v1/events", {
            "agent_id": agent_id,
            "action": action,
            "target": target,
            "status": status,
            "metadata": metadata or {},
        })
        return Event.from_dict(resp)

    # --- Metrics ---

    def log_metric(
        self,
        agent_id: str,
        tokens_used: int = 0,
        cost: float = 0.0,
        tool_calls: int = 0,
        files_accessed: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Metric:
        """Log agent metrics."""
        resp = self._request("POST", "/api/v1/metrics", {
            "agent_id": agent_id,
            "tokens_used": tokens_used,
            "cost": cost,
            "tool_calls": tool_calls,
            "files_accessed": files_accessed,
            "metadata": metadata or {},
        })
        return Metric.from_dict(resp)

    # --- Policy ---

    def check_policy(self, agent_id: str, action: str) -> PolicyResult:
        """Check if an action is allowed by policy."""
        resp = self._request("POST", "/api/v1/policy/check", {
            "agent_id": agent_id,
            "action": action,
        })
        return PolicyResult.from_dict(resp)
