"""Typed data models for AgentMolt API responses."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Agent:
    """Represents a registered agent."""
    id: str
    name: str
    model: str = ""
    status: str = "idle"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Agent":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Event:
    """Represents a logged event."""
    id: str = ""
    agent_id: str = ""
    action: str = ""
    target: str = ""
    status: str = "allowed"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Metric:
    """Represents logged metrics."""
    id: str = ""
    agent_id: str = ""
    tokens_used: int = 0
    cost: float = 0.0
    tool_calls: int = 0
    files_accessed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Metric":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class PolicyResult:
    """Result of a policy check."""
    allowed: bool = False
    reason: str = ""
    policy_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyResult":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})
