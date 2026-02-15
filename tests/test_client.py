"""Unit tests for AgentMolt client."""

import json
import os
import unittest
from unittest.mock import patch, MagicMock

from agentmolt import AgentMolt, AgentMoltError, AuthenticationError, NotFoundError
from agentmolt.models import Agent, Event, Metric, PolicyResult
from agentmolt.decorators import monitor
from agentmolt.killswitch import KillSwitch
from agentmolt.hooks import logging_hook_pre, logging_hook_post, timing_hook


def _mock_response(data: dict, status: int = 200):
    """Create a mock urllib response."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.status = status
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestAgentMoltInit(unittest.TestCase):
    def test_requires_api_key(self):
        with self.assertRaises(AuthenticationError):
            AgentMolt(api_key="")

    def test_env_api_key(self):
        with patch.dict(os.environ, {"AGENTMOLT_API_KEY": "am_test123"}):
            am = AgentMolt()
            self.assertEqual(am.api_key, "am_test123")

    def test_env_base_url(self):
        with patch.dict(os.environ, {"AGENTMOLT_API_KEY": "am_x", "AGENTMOLT_BASE_URL": "https://custom.dev"}):
            am = AgentMolt()
            self.assertEqual(am.base_url, "https://custom.dev")

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
        self.assertEqual(agent.name, "bot")

    @patch("urllib.request.urlopen")
    def test_list_agents(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"agents": [{"id": "a1", "name": "bot", "status": "idle"}]})
        agents = self.am.list_agents()
        self.assertEqual(len(agents), 1)
        self.assertIsInstance(agents[0], Agent)

    @patch("urllib.request.urlopen")
    def test_log_event(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"id": "e1", "agent_id": "a1", "action": "search"})
        event = self.am.log_event("a1", action="search")
        self.assertIsInstance(event, Event)

    @patch("urllib.request.urlopen")
    def test_log_metric(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"id": "m1", "agent_id": "a1", "tokens_used": 100})
        metric = self.am.log_metric("a1", tokens_used=100)
        self.assertIsInstance(metric, Metric)

    @patch("urllib.request.urlopen")
    def test_check_policy(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"allowed": True, "reason": "ok"})
        result = self.am.check_policy("a1", "search")
        self.assertIsInstance(result, PolicyResult)
        self.assertTrue(result.allowed)

    @patch("urllib.request.urlopen")
    def test_hooks(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"agents": []})
        calls = []
        self.am.add_hook("pre", lambda *a: calls.append("pre"))
        self.am.add_hook("post", lambda *a: calls.append("post"))
        self.am.list_agents()
        self.assertEqual(calls, ["pre", "post"])


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
        self.assertTrue(mock_urlopen.called)


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
