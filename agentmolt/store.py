"""SQLite-based local storage backend for AgentMolt."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import Agent, Event, Metric, PolicyResult

DEFAULT_DB_PATH = os.path.join(os.path.expanduser("~"), ".agentmolt", "agentmolt.db")


class Store:
    """Thread-safe SQLite storage for agents, events, metrics, and policies."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS agents (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        model TEXT DEFAULT '',
                        status TEXT DEFAULT 'idle',
                        metadata TEXT DEFAULT '{}',
                        created_at TEXT,
                        updated_at TEXT
                    );
                    CREATE TABLE IF NOT EXISTS events (
                        id TEXT PRIMARY KEY,
                        agent_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        target TEXT DEFAULT '',
                        status TEXT DEFAULT 'allowed',
                        metadata TEXT DEFAULT '{}',
                        created_at TEXT
                    );
                    CREATE TABLE IF NOT EXISTS metrics (
                        id TEXT PRIMARY KEY,
                        agent_id TEXT NOT NULL,
                        tokens_used INTEGER DEFAULT 0,
                        cost REAL DEFAULT 0.0,
                        tool_calls INTEGER DEFAULT 0,
                        files_accessed INTEGER DEFAULT 0,
                        metadata TEXT DEFAULT '{}',
                        created_at TEXT
                    );
                    CREATE TABLE IF NOT EXISTS policies (
                        id TEXT PRIMARY KEY,
                        rule_type TEXT NOT NULL,
                        value TEXT NOT NULL,
                        agent_id TEXT DEFAULT '',
                        created_at TEXT
                    );
                """)
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _uid() -> str:
        return uuid.uuid4().hex[:12]

    # --- Agents ---

    def create_agent(self, name: str, model: str = "", metadata: Optional[Dict[str, Any]] = None) -> Agent:
        aid = self._uid()
        now = self._now()
        meta = json.dumps(metadata or {})
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO agents (id, name, model, status, metadata, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                    (aid, name, model, "idle", meta, now, now),
                )
                conn.commit()
            finally:
                conn.close()
        return Agent(id=aid, name=name, model=model, status="idle", metadata=metadata or {}, created_at=now, updated_at=now)

    def list_agents(self) -> List[Agent]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute("SELECT * FROM agents ORDER BY created_at DESC").fetchall()
            finally:
                conn.close()
        return [Agent(id=r["id"], name=r["name"], model=r["model"], status=r["status"],
                      metadata=json.loads(r["metadata"]), created_at=r["created_at"], updated_at=r["updated_at"]) for r in rows]

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        with self._lock:
            conn = self._connect()
            try:
                r = conn.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
            finally:
                conn.close()
        if not r:
            return None
        return Agent(id=r["id"], name=r["name"], model=r["model"], status=r["status"],
                     metadata=json.loads(r["metadata"]), created_at=r["created_at"], updated_at=r["updated_at"])

    def update_agent_status(self, agent_id: str, status: str) -> Optional[Agent]:
        now = self._now()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("UPDATE agents SET status=?, updated_at=? WHERE id=?", (status, now, agent_id))
                conn.commit()
            finally:
                conn.close()
        return self.get_agent(agent_id)

    def kill_agent(self, agent_id: str) -> Dict[str, Any]:
        self.update_agent_status(agent_id, "killed")
        return {"status": "killed", "agent_id": agent_id}

    # --- Events ---

    def create_event(self, agent_id: str, action: str, target: str = "", status: str = "allowed",
                     metadata: Optional[Dict[str, Any]] = None) -> Event:
        eid = self._uid()
        now = self._now()
        meta = json.dumps(metadata or {})
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO events (id, agent_id, action, target, status, metadata, created_at) VALUES (?,?,?,?,?,?,?)",
                    (eid, agent_id, action, target, status, meta, now),
                )
                conn.commit()
            finally:
                conn.close()
        return Event(id=eid, agent_id=agent_id, action=action, target=target, status=status,
                     metadata=metadata or {}, created_at=now)

    def list_events(self, agent_id: str) -> List[Event]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute("SELECT * FROM events WHERE agent_id=? ORDER BY created_at DESC", (agent_id,)).fetchall()
            finally:
                conn.close()
        return [Event(id=r["id"], agent_id=r["agent_id"], action=r["action"], target=r["target"],
                      status=r["status"], metadata=json.loads(r["metadata"]), created_at=r["created_at"]) for r in rows]

    # --- Metrics ---

    def create_metric(self, agent_id: str, tokens_used: int = 0, cost: float = 0.0,
                      tool_calls: int = 0, files_accessed: int = 0,
                      metadata: Optional[Dict[str, Any]] = None) -> Metric:
        mid = self._uid()
        now = self._now()
        meta = json.dumps(metadata or {})
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO metrics (id, agent_id, tokens_used, cost, tool_calls, files_accessed, metadata, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (mid, agent_id, tokens_used, cost, tool_calls, files_accessed, meta, now),
                )
                conn.commit()
            finally:
                conn.close()
        return Metric(id=mid, agent_id=agent_id, tokens_used=tokens_used, cost=cost,
                      tool_calls=tool_calls, files_accessed=files_accessed, metadata=metadata or {}, created_at=now)

    def get_metrics_summary(self, agent_id: str) -> Dict[str, Any]:
        with self._lock:
            conn = self._connect()
            try:
                r = conn.execute(
                    "SELECT COALESCE(SUM(tokens_used),0) as tokens, COALESCE(SUM(cost),0) as cost, "
                    "COALESCE(SUM(tool_calls),0) as tools, COUNT(*) as count FROM metrics WHERE agent_id=?",
                    (agent_id,),
                ).fetchone()
            finally:
                conn.close()
        return {"tokens_used": r["tokens"], "cost": r["cost"], "tool_calls": r["tools"], "count": r["count"]}

    # --- Policies ---

    def add_policy(self, rule_type: str, value: str, agent_id: str = "") -> Dict[str, Any]:
        """Add a policy rule. rule_type: allowlist, denylist, cost_limit, token_limit."""
        pid = self._uid()
        now = self._now()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO policies (id, rule_type, value, agent_id, created_at) VALUES (?,?,?,?,?)",
                    (pid, rule_type, value, agent_id, now),
                )
                conn.commit()
            finally:
                conn.close()
        return {"id": pid, "rule_type": rule_type, "value": value, "agent_id": agent_id}

    def list_policies(self, agent_id: str = "") -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                if agent_id:
                    rows = conn.execute(
                        "SELECT * FROM policies WHERE agent_id=? OR agent_id='' ORDER BY created_at", (agent_id,)
                    ).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM policies ORDER BY created_at").fetchall()
            finally:
                conn.close()
        return [dict(r) for r in rows]

    def check_policy(self, agent_id: str, action: str) -> PolicyResult:
        """Evaluate policies for an action. Returns PolicyResult."""
        policies = self.list_policies(agent_id)
        for p in policies:
            if p["rule_type"] == "denylist" and action == p["value"]:
                return PolicyResult(allowed=False, reason=f"Action '{action}' is denied by policy {p['id']}", policy_id=p["id"])
        for p in policies:
            if p["rule_type"] == "allowlist":
                # If any allowlist exists, action must be in one
                allowlist_values = [pp["value"] for pp in policies if pp["rule_type"] == "allowlist"]
                if action not in allowlist_values:
                    return PolicyResult(allowed=False, reason=f"Action '{action}' not in allowlist", policy_id=p["id"])
                break
        # Check cost/token limits against accumulated metrics
        for p in policies:
            if p["rule_type"] == "cost_limit":
                summary = self.get_metrics_summary(agent_id)
                limit = float(p["value"])
                if summary["cost"] >= limit:
                    return PolicyResult(allowed=False, reason=f"Cost limit ${limit} exceeded (${summary['cost']})", policy_id=p["id"])
            elif p["rule_type"] == "token_limit":
                summary = self.get_metrics_summary(agent_id)
                limit = int(p["value"])
                if summary["tokens_used"] >= limit:
                    return PolicyResult(allowed=False, reason=f"Token limit {limit} exceeded ({summary['tokens_used']})", policy_id=p["id"])
        return PolicyResult(allowed=True, reason="allowed")

    # --- Stats ---

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            conn = self._connect()
            try:
                agents = conn.execute("SELECT COUNT(*) as c FROM agents").fetchone()["c"]
                events = conn.execute("SELECT COUNT(*) as c FROM events").fetchone()["c"]
                metrics = conn.execute("SELECT COUNT(*) as c FROM metrics").fetchone()["c"]
                policies = conn.execute("SELECT COUNT(*) as c FROM policies").fetchone()["c"]
            finally:
                conn.close()
        return {"agents": agents, "events": events, "metrics": metrics, "policies": policies}
