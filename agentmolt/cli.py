"""AgentMolt CLI — requires ``pip install agentmolt[cli]``."""

from __future__ import annotations

import json
import sys

try:
    import click
except ImportError:
    print("CLI requires click: pip install agentmolt[cli]", file=sys.stderr)
    sys.exit(1)

from .client import AgentMolt


def _client() -> AgentMolt:
    try:
        return AgentMolt()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.group()
@click.version_option(package_name="agentmolt")
def main() -> None:
    """AgentMolt — Control plane for AI agent teams."""


# --- agents ---

@main.group()
def agents() -> None:
    """Manage agents."""


@agents.command("list")
def agents_list() -> None:
    """List all agents."""
    am = _client()
    for a in am.list_agents():
        click.echo(f"{a.id}\t{a.status}\t{a.name}\t{a.model}")


@agents.command("get")
@click.argument("agent_id")
def agents_get(agent_id: str) -> None:
    """Get agent details."""
    am = _client()
    a = am.get_agent(agent_id)
    click.echo(json.dumps(a.__dict__, indent=2))


# --- kill ---

@main.command()
@click.argument("agent_id")
def kill(agent_id: str) -> None:
    """Kill an agent immediately."""
    am = _client()
    resp = am.kill(agent_id)
    click.echo(json.dumps(resp, indent=2))


# --- status ---

@main.command()
@click.argument("agent_id")
def status(agent_id: str) -> None:
    """Get agent status."""
    am = _client()
    a = am.get_agent(agent_id)
    click.echo(f"{a.name}: {a.status}")


if __name__ == "__main__":
    main()
