# 🔥 AgentMolt — Control Plane for AI Agent Teams

Monitor, govern, and kill-switch your AI agents. Works **fully offline** with local storage, or connect to the AgentMolt cloud API.

## Quick Start (Local — No API Key Needed!)

```bash
pip install agentmolt
agentmolt init
```

```python
from agentmolt import AgentMoltLocal

am = AgentMoltLocal()

# Register an agent
agent = am.register_agent("my-agent", model="gpt-4")

# Log events
am.log_event(agent.id, action="tool_call", target="search_api")

# Log metrics
am.log_metric(agent.id, tokens_used=500, cost=0.01)

# Check policies
result = am.check_policy(agent.id, "delete_files")
if not result.allowed:
    print(f"Blocked: {result.reason}")

# Kill switch
am.kill(agent.id)
```

## CLI

```bash
agentmolt init                    # Initialize local database
agentmolt agents                  # List all agents
agentmolt events <agent_id>      # Show events for an agent
agentmolt kill <agent_id>        # Kill an agent
agentmolt status                  # Summary stats
agentmolt policy add denylist delete_files   # Block an action
agentmolt policy add cost_limit 10.00        # Set cost limit
agentmolt policy add token_limit 100000      # Set token limit
agentmolt policy list             # List all policy rules
```

## Policy Engine

Built-in policy rules, no server required:

- **denylist** — Block specific actions
- **allowlist** — Only allow listed actions (if any allowlist rule exists, unlisted actions are denied)
- **cost_limit** — Block when cumulative cost exceeds threshold
- **token_limit** — Block when cumulative tokens exceed threshold

```python
am.add_policy("denylist", "delete_files")
am.add_policy("cost_limit", "5.00")

result = am.check_policy(agent.id, "delete_files")
# PolicyResult(allowed=False, reason="Action 'delete_files' is denied by policy ...")
```

## Remote API (Advanced)

For team dashboards and cloud features, use the remote client:

```python
from agentmolt import AgentMolt

am = AgentMolt(api_key="am_...")  # or set AGENTMOLT_API_KEY env var
agent = am.register_agent("my-agent", model="gpt-4")
```

## Installation

```bash
pip install agentmolt           # Core (zero dependencies)
pip install agentmolt[cli]      # CLI support (adds click)
pip install agentmolt[async]    # Async client (adds aiohttp)
pip install agentmolt[all]      # Everything
```

## Features

- 🏠 **Local-first** — SQLite storage, works offline
- 🔌 **Zero dependencies** — stdlib only for core
- 🛡️ **Policy engine** — allowlist, denylist, cost/token limits
- 🔴 **Kill switch** — stop agents instantly
- 📊 **Metrics** — track tokens, costs, tool calls
- 📝 **Event logging** — full audit trail
- 🌐 **Remote API** — optional cloud dashboard
- 🐍 **Python 3.8+** compatible

## License

Apache-2.0
