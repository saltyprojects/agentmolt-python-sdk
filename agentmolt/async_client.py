"""Async client for AgentMolt using aiohttp."""

from __future__ import annotations

import json
import logging
import os
import asyncio
from typing import Any, Callable, Dict, List, Optional

from .exceptions import AgentMoltError, AuthenticationError, NotFoundError
from .models import Agent, Event, Metric, PolicyResult

logger = logging.getLogger("agentmolt.async")

DEFAULT_BASE_URL = "https://agentmolt.dev"
_MAX_RETRIES = 3
_BACKOFF_BASE = 0.5
_RETRYABLE_CODES = {429, 500, 502, 503, 504}


class AsyncAgentMolt:
    """Async client for the AgentMolt API.

    Requires ``aiohttp`` (install with ``pip install agentmolt[async]``).

    Usage::

        async with AsyncAgentMolt(api_key="am_...") as am:
            agent = await am.register_agent("my-agent")
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
        self._session: Any = None

    async def __aenter__(self) -> "AsyncAgentMolt":
        import aiohttp
        self._session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    def _ensure_session(self) -> Any:
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._session

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def _request(self, method: str, path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        session = self._ensure_session()
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                async with session.request(method, url, json=data) as resp:
                    body = await resp.text()
                    if resp.status >= 400:
                        try:
                            msg = json.loads(body).get("error", body)
                        except json.JSONDecodeError:
                            msg = body
                        if resp.status in _RETRYABLE_CODES and attempt < self.max_retries - 1:
                            wait = _BACKOFF_BASE * (2 ** attempt)
                            logger.warning("Retryable %s on %s %s, retry in %.1fs", resp.status, method, path, wait)
                            await asyncio.sleep(wait)
                            last_exc = AgentMoltError(msg, status_code=resp.status)
                            continue
                        if resp.status == 401:
                            raise AuthenticationError(msg, status_code=resp.status)
                        elif resp.status == 404:
                            raise NotFoundError(msg, status_code=resp.status)
                        else:
                            raise AgentMoltError(msg, status_code=resp.status)
                    return json.loads(body)
            except (OSError, Exception) as e:
                if isinstance(e, AgentMoltError):
                    raise
                if attempt < self.max_retries - 1:
                    wait = _BACKOFF_BASE * (2 ** attempt)
                    logger.warning("Connection error on %s %s, retry in %.1fs", method, path, wait)
                    await asyncio.sleep(wait)
                    last_exc = AgentMoltError(f"Connection error: {e}")
                    continue
                raise AgentMoltError(f"Connection error: {e}")

        raise last_exc or AgentMoltError("Request failed after retries")

    async def register_agent(self, name: str, model: str = "", metadata: Optional[Dict[str, Any]] = None) -> Agent:
        resp = await self._request("POST", "/api/v1/agents/register", {"name": name, "model": model, "metadata": metadata or {}})
        return Agent.from_dict(resp)

    async def list_agents(self) -> List[Agent]:
        resp = await self._request("GET", "/api/v1/agents")
        return [Agent.from_dict(a) for a in resp.get("agents", [])]

    async def get_agent(self, agent_id: str) -> Agent:
        return Agent.from_dict(await self._request("GET", f"/api/v1/agents/{agent_id}"))

    async def update_status(self, agent_id: str, status: str) -> Agent:
        return Agent.from_dict(await self._request("POST", f"/api/v1/agents/{agent_id}/status", {"status": status}))

    async def kill(self, agent_id: str) -> Dict[str, Any]:
        return await self._request("POST", f"/api/v1/agents/{agent_id}/kill")

    async def log_event(self, agent_id: str, action: str, target: str = "", status: str = "allowed", metadata: Optional[Dict[str, Any]] = None) -> Event:
        resp = await self._request("POST", "/api/v1/events", {"agent_id": agent_id, "action": action, "target": target, "status": status, "metadata": metadata or {}})
        return Event.from_dict(resp)

    async def log_metric(self, agent_id: str, tokens_used: int = 0, cost: float = 0.0, tool_calls: int = 0, files_accessed: int = 0, metadata: Optional[Dict[str, Any]] = None) -> Metric:
        resp = await self._request("POST", "/api/v1/metrics", {"agent_id": agent_id, "tokens_used": tokens_used, "cost": cost, "tool_calls": tool_calls, "files_accessed": files_accessed, "metadata": metadata or {}})
        return Metric.from_dict(resp)

    async def check_policy(self, agent_id: str, action: str) -> PolicyResult:
        resp = await self._request("POST", "/api/v1/policy/check", {"agent_id": agent_id, "action": action})
        return PolicyResult.from_dict(resp)
