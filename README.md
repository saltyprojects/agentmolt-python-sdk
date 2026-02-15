# 🛡️ AgentMolt Python SDK

Control plane for AI agent teams. Monitor, govern, and kill-switch your AI agents.

## Install

```bash
pip install agentmolt

# With async support
pip install agentmolt[async]

# With CLI
pip install agentmolt[cli]

# Everything
pip install agentmolt[all]
```

## Quick Start

```python
from agentmolt import AgentMolt

am = AgentMolt(api_key="am_...")

# Register an agent
agent = am.register_agent("my-research-bot", model="gpt-4")
print(f"Agent ID: {agent.id}")  # Typed dataclass, not raw dict!

# Log events
am.log_event(agent.id, action="web_search", target="arxiv.org")

# Log metrics
am.log_metric(agent.id, tokens_used=1500, cost=0.045, tool_calls=3)

# Check policy
policy = am.check_policy(agent.id, action="send_email")
if policy.allowed:
    send_email()

# Kill switch
am.kill(agent.id)
```

## Environment Variables

Set `AGENTMOLT_API_KEY` and `AGENTMOLT_BASE_URL` to skip passing them explicitly:

```bash
export AGENTMOLT_API_KEY=am_...
export AGENTMOLT_BASE_URL=https://your-instance.com
```

```python
am = AgentMolt()  # reads from env
```

## Context Manager

```python
with AgentMolt(api_key="am_...") as am:
    agent = am.register_agent("bot")
```

## Async Client

```python
from agentmolt.async_client import AsyncAgentMolt

async with AsyncAgentMolt(api_key="am_...") as am:
    agent = await am.register_agent("async-bot")
    await am.log_event(agent.id, action="search")
```

## Decorators — Auto-Monitor Functions

```python
from agentmolt import AgentMolt, monitor

am = AgentMolt(api_key="am_...")

@monitor(am, agent_id="agent-123")
def search(query: str) -> str:
    return do_search(query)

# Automatically logs events + metrics when search() is called
search("latest papers")
```

## Kill Switch — Background Polling

```python
from agentmolt import AgentMolt, KillSwitch

am = AgentMolt(api_key="am_...")
ks = KillSwitch(am, agent_id="agent-123", poll_interval=5)
ks.start()

# Your agent runs normally...
# If someone kills it via the dashboard, SystemExit is raised automatically.
# Custom handler:
ks = KillSwitch(am, "agent-123", on_kill=lambda: cleanup_and_exit())
```

## Hooks / Middleware

```python
from agentmolt.hooks import logging_hook_pre, logging_hook_post, timing_hook

am = AgentMolt(api_key="am_...")
am.add_hook("pre", logging_hook_pre)
am.add_hook("post", logging_hook_post)

pre, post = timing_hook()
am.add_hook("pre", pre)
am.add_hook("post", post)
```

## CLI

```bash
# List agents
agentmolt agents list

# Get agent details
agentmolt agents get <agent-id>

# Kill an agent
agentmolt kill <agent-id>

# Check status
agentmolt status <agent-id>
```

## Retry & Error Handling

The client automatically retries on 429/5xx errors with exponential backoff (default 3 retries). All API errors raise typed exceptions:

```python
from agentmolt import AgentMoltError, AuthenticationError, NotFoundError

try:
    am.get_agent("nonexistent")
except NotFoundError:
    print("Agent not found")
except AgentMoltError as e:
    print(f"API error {e.status_code}: {e}")
```

## Typed Models

All responses return typed dataclasses (`Agent`, `Event`, `Metric`, `PolicyResult`) instead of raw dicts. Full PEP 561 typing support with `py.typed` marker.

## Self-Hosted

```python
am = AgentMolt(api_key="am_...", base_url="https://your-instance.com")
```

## License

Apache 2.0
