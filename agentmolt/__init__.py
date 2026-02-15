"""AgentMolt — Control plane for AI agent teams."""

from .client import AgentMolt
from .exceptions import AgentMoltError, AuthenticationError, NotFoundError, PolicyDeniedError
from .models import Agent, Event, Metric, PolicyResult
from .decorators import monitor
from .killswitch import KillSwitch

__version__ = "0.2.0"
__all__ = [
    "AgentMolt",
    "AgentMoltError",
    "AuthenticationError",
    "NotFoundError",
    "PolicyDeniedError",
    "Agent",
    "Event",
    "Metric",
    "PolicyResult",
    "monitor",
    "KillSwitch",
]
