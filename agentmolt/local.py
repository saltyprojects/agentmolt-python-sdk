"""AgentMolt local client — standalone, no server required."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .exceptions import NotFoundError
from .models import Agent, Event, Metric, PolicyResult
from .store import Store, DEFAULT_DB_PATH


class AgentMoltLocal:
    """Local client with the same interface as AgentMolt, backed by SQLite.

    Usage::

        from agentmolt import AgentMoltLocal

        am = AgentMoltLocal()  # no API key needed!
        agent = am.register_agent("my-agent", model="gpt-4")
        am.log_event(agent.id, action="tool_call", target="search_api")
        am.kill(agent.id)
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.store = Store(db_path)
        self._hooks: Dict[str, List[Callable[..., Any]]] = {"pre": [], "post": []}

    def __enter__(self) -> "AgentMoltLocal":
        return self

    def __exit__(self, *exc: Any) -> None:
        pass

    def add_hook(self, stage: str, fn: Callable[..., Any]) -> None:
        if stage not in self._hooks:
            raise ValueError("stage must be 'pre' or 'post'")
        self._hooks[stage].append(fn)

    # --- Agents ---

    def register_agent(self, name: str, model: str = "", metadata: Optional[Dict[str, Any]] = None) -> Agent:
        return self.store.create_agent(name, model, metadata)

    def list_agents(self) -> List[Agent]:
        return self.store.list_agents()

    def get_agent(self, agent_id: str) -> Agent:
        agent = self.store.get_agent(agent_id)
        if not agent:
            raise NotFoundError(f"Agent {agent_id} not found")
        return agent

    def update_status(self, agent_id: str, status: str) -> Agent:
        agent = self.store.update_agent_status(agent_id, status)
        if not agent:
            raise NotFoundError(f"Agent {agent_id} not found")
        return agent

    def kill(self, agent_id: str) -> Dict[str, Any]:
        agent = self.store.get_agent(agent_id)
        if not agent:
            raise NotFoundError(f"Agent {agent_id} not found")
        return self.store.kill_agent(agent_id)

    # --- Events ---

    def log_event(self, agent_id: str, action: str, target: str = "",
                  status: str = "allowed", metadata: Optional[Dict[str, Any]] = None) -> Event:
        return self.store.create_event(agent_id, action, target, status, metadata)

    def list_events(self, agent_id: str) -> List[Event]:
        return self.store.list_events(agent_id)

    # --- Metrics ---

    def log_metric(self, agent_id: str, tokens_used: int = 0, cost: float = 0.0,
                   tool_calls: int = 0, files_accessed: int = 0,
                   metadata: Optional[Dict[str, Any]] = None) -> Metric:
        return self.store.create_metric(agent_id, tokens_used, cost, tool_calls, files_accessed, metadata)

    # --- Policy ---

    def check_policy(self, agent_id: str, action: str) -> PolicyResult:
        return self.store.check_policy(agent_id, action)

    def add_policy(self, rule_type: str, value: str, agent_id: str = "") -> Dict[str, Any]:
        return self.store.add_policy(rule_type, value, agent_id)

    def list_policies(self, agent_id: str = "") -> List[Dict[str, Any]]:
        return self.store.list_policies(agent_id)
