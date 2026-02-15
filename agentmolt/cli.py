"""AgentMolt CLI — requires ``pip install agentmolt[cli]``."""

from __future__ import annotations

import json
import sys

try:
    import click
except ImportError:
    print("CLI requires click: pip install agentmolt[cli]", file=sys.stderr)
    sys.exit(1)

from .local import AgentMoltLocal
from .store import DEFAULT_DB_PATH


def _local() -> AgentMoltLocal:
    return AgentMoltLocal()


@click.group()
@click.version_option(package_name="agentmolt")
def main() -> None:
    """AgentMolt — Control plane for AI agent teams."""


# --- init ---

@main.command()
def init() -> None:
    """Initialize local AgentMolt database."""
    am = _local()
    click.echo(f"✓ Database initialized at {am.store.db_path}")


# --- agents ---

@main.command("agents")
def agents_list() -> None:
    """List all agents."""
    am = _local()
    agents = am.list_agents()
    if not agents:
        click.echo("No agents registered.")
        return
    for a in agents:
        click.echo(f"{a.id}\t{a.status}\t{a.name}\t{a.model}")


# --- events ---

@main.command("events")
@click.argument("agent_id")
def events_list(agent_id: str) -> None:
    """Show events for an agent."""
    am = _local()
    events = am.list_events(agent_id)
    if not events:
        click.echo("No events found.")
        return
    for e in events:
        click.echo(f"{e.created_at}\t{e.action}\t{e.target}\t{e.status}")


# --- kill ---

@main.command()
@click.argument("agent_id")
def kill(agent_id: str) -> None:
    """Kill an agent immediately."""
    am = _local()
    try:
        resp = am.kill(agent_id)
        click.echo(f"✓ Agent {agent_id} killed.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# --- status ---

@main.command()
def status() -> None:
    """Show summary stats."""
    am = _local()
    stats = am.store.stats()
    click.echo(f"Agents:   {stats['agents']}")
    click.echo(f"Events:   {stats['events']}")
    click.echo(f"Metrics:  {stats['metrics']}")
    click.echo(f"Policies: {stats['policies']}")
    click.echo(f"Database: {am.store.db_path}")


# --- policy ---

@main.group()
def policy() -> None:
    """Manage policies."""


@policy.command("add")
@click.argument("rule_type")
@click.argument("value")
@click.option("--agent-id", default="", help="Scope to a specific agent.")
def policy_add(rule_type: str, value: str, agent_id: str) -> None:
    """Add a policy rule (allowlist, denylist, cost_limit, token_limit)."""
    am = _local()
    result = am.add_policy(rule_type, value, agent_id)
    click.echo(f"✓ Policy added: {result['rule_type']} = {result['value']} (id: {result['id']})")


@policy.command("list")
def policy_list() -> None:
    """List all policy rules."""
    am = _local()
    policies = am.list_policies()
    if not policies:
        click.echo("No policies configured.")
        return
    for p in policies:
        scope = f" (agent: {p['agent_id']})" if p.get("agent_id") else " (global)"
        click.echo(f"{p['id']}\t{p['rule_type']}\t{p['value']}{scope}")


if __name__ == "__main__":
    main()
