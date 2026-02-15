"""Unit tests for AgentMolt client (remote and local)."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from agentmolt import AgentMolt, AgentMoltLocal, AgentMoltError, AuthenticationError, NotFoundError
from agentmolt.models import Agent, Event, Metric, PolicyResult
from agentmolt.decorators import monitor
from agentmolt.killswitch import KillSwitch
from agentmolt.hooks import logging_hook_pre, logging_hook_post, timing_hook


def _mock_response(data: dict, status: int = 200):
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.status = status
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ===== Remote Client Tests =====

class TestAgentMoltInit(unittest.TestCase):
    def test_requires_api_key(self):
        with self.assertRaises(AuthenticationError):
            AgentMolt(api_key="")

    def test_env_api_key(self):
        with patch.dict(os.environ, {"AGENTMOLT_API_KEY": "am_test123"}):
            am = AgentMolt()
            self.assertEqual(am.api_key, "am_test123")

    def test_context_manager(self):
        with AgentMolt(api_key="am_test") as am:
            self.assertIsInstance(am, AgentMolt)


class TestAgentMoltRequests(unittest.TestCase):
    def setUp(self):
        self.am = AgentMolt(api_key="am_test", max_retries=1)

    @patch("urllib.request.urlopen")
    def test_register_agent(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"id": "a1", "name": "bot", "model": "gpt-4", "status": "idle"})
        agent = self.am.register_agent("bot", model="gpt-4")
        self.assertIsInstance(agent, Agent)
        self.assertEqual(agent.id, "a1")

    @patch("urllib.request.urlopen")
    def test_list_agents(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"agents": [{"id": "a1", "name": "bot", "status": "idle"}]})
        agents = self.am.list_agents()
        self.assertEqual(len(agents), 1)

    @patch("urllib.request.urlopen")
    def test_log_event(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"id": "e1", "agent_id": "a1", "action": "search"})
        event = self.am.log_event("a1", action="search")
        self.assertIsInstance(event, Event)

    @patch("urllib.request.urlopen")
    def test_check_policy(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"allowed": True, "reason": "ok"})
        result = self.am.check_policy("a1", "search")
        self.assertTrue(result.allowed)

    @patch("urllib.request.urlopen")
    def test_hooks(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"agents": []})
        calls = []
        self.am.add_hook("pre", lambda *a: calls.append("pre"))
        self.am.add_hook("post", lambda *a: calls.append("post"))
        self.am.list_agents()
        self.assertEqual(calls, ["pre", "post"])


# ===== Local Client Tests =====

class TestAgentMoltLocal(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.am = AgentMoltLocal(db_path=self.db_path)

    def test_register_and_get_agent(self):
        agent = self.am.register_agent("test-bot", model="gpt-4")
        self.assertEqual(agent.name, "test-bot")
        self.assertEqual(agent.model, "gpt-4")
        self.assertEqual(agent.status, "idle")

        fetched = self.am.get_agent(agent.id)
        self.assertEqual(fetched.id, agent.id)

    def test_list_agents(self):
        self.am.register_agent("bot-1")
        self.am.register_agent("bot-2")
        agents = self.am.list_agents()
        self.assertEqual(len(agents), 2)

    def test_update_status(self):
        agent = self.am.register_agent("bot")
        updated = self.am.update_status(agent.id, "running")
        self.assertEqual(updated.status, "running")

    def test_kill_agent(self):
        agent = self.am.register_agent("bot")
        result = self.am.kill(agent.id)
        self.assertEqual(result["status"], "killed")
        killed = self.am.get_agent(agent.id)
        self.assertEqual(killed.status, "killed")

    def test_kill_nonexistent(self):
        with self.assertRaises(NotFoundError):
            self.am.kill("nonexistent")

    def test_get_nonexistent(self):
        with self.assertRaises(NotFoundError):
            self.am.get_agent("nonexistent")

    def test_log_event(self):
        agent = self.am.register_agent("bot")
        event = self.am.log_event(agent.id, action="tool_call", target="api")
        self.assertIsInstance(event, Event)
        self.assertEqual(event.action, "tool_call")

    def test_list_events(self):
        agent = self.am.register_agent("bot")
        self.am.log_event(agent.id, action="a1")
        self.am.log_event(agent.id, action="a2")
        events = self.am.list_events(agent.id)
        self.assertEqual(len(events), 2)

    def test_log_metric(self):
        agent = self.am.register_agent("bot")
        metric = self.am.log_metric(agent.id, tokens_used=500, cost=0.01)
        self.assertIsInstance(metric, Metric)
        self.assertEqual(metric.tokens_used, 500)

    def test_context_manager(self):
        with AgentMoltLocal(db_path=self.db_path) as am:
            self.assertIsInstance(am, AgentMoltLocal)


class TestLocalPolicy(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.am = AgentMoltLocal(db_path=self.db_path)

    def test_default_allow(self):
        result = self.am.check_policy("a1", "anything")
        self.assertTrue(result.allowed)

    def test_denylist(self):
        self.am.add_policy("denylist", "delete_files")
        result = self.am.check_policy("a1", "delete_files")
        self.assertFalse(result.allowed)
        self.assertIn("denied", result.reason)

    def test_denylist_other_allowed(self):
        self.am.add_policy("denylist", "delete_files")
        result = self.am.check_policy("a1", "read_files")
        self.assertTrue(result.allowed)

    def test_allowlist(self):
        self.am.add_policy("allowlist", "search")
        self.am.add_policy("allowlist", "read")
        result = self.am.check_policy("a1", "search")
        self.assertTrue(result.allowed)
        result = self.am.check_policy("a1", "delete")
        self.assertFalse(result.allowed)

    def test_cost_limit(self):
        agent = self.am.register_agent("bot")
        self.am.add_policy("cost_limit", "1.00")
        self.am.log_metric(agent.id, cost=1.50)
        result = self.am.check_policy(agent.id, "anything")
        self.assertFalse(result.allowed)
        self.assertIn("Cost limit", result.reason)

    def test_token_limit(self):
        agent = self.am.register_agent("bot")
        self.am.add_policy("token_limit", "1000")
        self.am.log_metric(agent.id, tokens_used=1500)
        result = self.am.check_policy(agent.id, "anything")
        self.assertFalse(result.allowed)
        self.assertIn("Token limit", result.reason)

    def test_list_policies(self):
        self.am.add_policy("denylist", "x")
        self.am.add_policy("allowlist", "y")
        policies = self.am.list_policies()
        self.assertEqual(len(policies), 2)


# ===== Model Tests =====

class TestModels(unittest.TestCase):
    def test_agent_from_dict(self):
        a = Agent.from_dict({"id": "x", "name": "bot", "extra_field": 1})
        self.assertEqual(a.id, "x")

    def test_policy_result(self):
        p = PolicyResult.from_dict({"allowed": False, "reason": "blocked"})
        self.assertFalse(p.allowed)


class TestDecorators(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_monitor_calls_log(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"id": "e1", "agent_id": "a1", "action": "test"})
        am = AgentMolt(api_key="am_test", max_retries=1)

        @monitor(am, agent_id="a1")
        def my_func():
            return 42

        result = my_func()
        self.assertEqual(result, 42)


class TestKillSwitch(unittest.TestCase):
    def test_start_stop(self):
        client = MagicMock()
        client.get_agent.return_value = Agent(id="a1", name="bot", status="running")
        ks = KillSwitch(client, "a1", poll_interval=0.1)
        ks.start()
        import time; time.sleep(0.3)
        ks.stop()
        self.assertTrue(client.get_agent.called)


class TestHooks(unittest.TestCase):
    def test_timing_hook(self):
        pre, post = timing_hook()
        pre("GET", "/test", None)
        post("GET", "/test", None, {})


if __name__ == "__main__":
    unittest.main()
