"""Unit tests for WorkflowRegistry and WorkflowTriggerEngine."""

import os
import shutil
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

from locallm.core.orchestrator.registry import WorkflowRegistry
from locallm.core.orchestrator.trigger_engine import WorkflowTriggerEngine, _is_cron_due
from datetime import datetime


class TestWorkflowRegistry(unittest.TestCase):
    """Test registry persistence, CRUD operations, and execution history."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.registry = WorkflowRegistry(base_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_auto_seed_presets(self):
        """Verify pre-built workflows are automatically seeded."""
        workflows = self.registry.list_workflows()
        self.assertGreaterEqual(len(workflows), 2)
        ids = [w["id"] for w in workflows]
        self.assertIn("fullstack-code-audit", ids)
        self.assertIn("telegram-incident-responder", ids)

    def test_crud_lifecycle(self):
        """Verify create, read, update, delete on custom workflow."""
        test_wf = {
            "id": "custom-test-workflow",
            "name": "Custom Test Workflow",
            "description": "Test description",
            "isActive": False,
            "nodes": [
                {"id": "n1", "category": "triggers", "tag": "intake", "title": "Trigger Node"}
            ],
            "edges": [],
        }

        # Create
        created = self.registry.save_workflow(test_wf)
        self.assertEqual(created["id"], "custom-test-workflow")
        self.assertIn("updated_at", created)

        # Read
        fetched = self.registry.get_workflow("custom-test-workflow")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["name"], "Custom Test Workflow")

        # Toggle Active
        status = self.registry.toggle_active("custom-test-workflow")
        self.assertTrue(status)
        refetched = self.registry.get_workflow("custom-test-workflow")
        self.assertTrue(refetched["isActive"])

        # Active workflows filter
        actives = self.registry.get_active_workflows()
        active_ids = [w["id"] for w in actives]
        self.assertIn("custom-test-workflow", active_ids)

        # Delete
        deleted = self.registry.delete_workflow("custom-test-workflow")
        self.assertTrue(deleted)
        self.assertIsNone(self.registry.get_workflow("custom-test-workflow"))

    def test_execution_history_recording(self):
        """Verify recording runs and retrieving history logs."""
        record = {
            "run_id": "run-test-123",
            "workflow_id": "custom-test-workflow",
            "workflow_title": "Custom Test Workflow",
            "trigger_source": "manual",
            "status": "success",
            "started_at": "2026-10-16T10:00:00",
            "ended_at": "2026-10-16T10:00:05",
            "duration_seconds": 5.0,
            "steps_executed": 3,
            "logs": [{"agent": "Intake", "message": "Objective received"}],
            "artifacts": [{"name": "result.txt", "path": "/tmp/result.txt"}],
        }

        self.registry.record_execution(record)
        history = self.registry.get_history(limit=10)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["run_id"], "run-test-123")

        # By run_id
        fetched_run = self.registry.get_execution("run-test-123")
        self.assertIsNotNone(fetched_run)
        self.assertEqual(fetched_run["status"], "success")


class TestWorkflowTriggerEngine(unittest.TestCase):
    """Test background trigger matching for messaging, webhook, and cron."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.registry = WorkflowRegistry(base_dir=self.temp_dir)
        self.engine = WorkflowTriggerEngine(registry=self.registry)

    def tearDown(self):
        self.engine.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cron_due_evaluator(self):
        """Verify cron expression due calculation."""
        # Wildcard cron "* * * * *" should be due
        now = datetime(2026, 10, 16, 14, 30, 0)
        self.assertTrue(_is_cron_due("* * * * *", now, None))

        # Hourly cron "30 * * * *" is due at 14:30
        self.assertTrue(_is_cron_due("30 * * * *", now, None))

        # Hourly cron "15 * * * *" is not due at 14:30
        self.assertFalse(_is_cron_due("15 * * * *", now, None))

        # If already ran in this minute, should not be due
        self.assertFalse(_is_cron_due("* * * * *", now, now))

    @patch("locallm.core.orchestrator.graph_executor.WorkflowGraphExecutor.run")
    def test_messaging_trigger_match(self, mock_run):
        """Verify inbound chat triggers active workflow with messaging-trigger."""
        mock_run.return_value = {
            "success": True,
            "steps_executed": 2,
            "state": {"context_variables": {"final_chat_message": "Automated reply sent."}},
            "logs": [],
            "artifacts": [],
        }

        wf = {
            "id": "telegram-responder",
            "name": "Telegram Auto Responder",
            "isActive": True,
            "nodes": [
                {
                    "id": "t1",
                    "category": "triggers",
                    "tag": "messaging-trigger",
                    "title": "Telegram Inbound",
                    "properties": {
                        "inputs": {"keyword": "deploy"},
                        "options": {"platform": "telegram"},
                    },
                },
                {"id": "o1", "category": "outputs", "tag": "chat-output", "title": "Reply"},
            ],
            "edges": [{"from": "t1", "to": "o1"}],
        }
        self.registry.save_workflow(wf)

        # Should not trigger on non-matching keyword
        non_match = self.engine.match_and_trigger_messaging("telegram", "user123", "hello world")
        self.assertIsNone(non_match)

        # Should not trigger on different platform
        wrong_platform = self.engine.match_and_trigger_messaging("whatsapp", "user123", "deploy now")
        self.assertIsNone(wrong_platform)

        # Should trigger on telegram + keyword
        match = self.engine.match_and_trigger_messaging("telegram", "user123", "please deploy project")
        self.assertIsNotNone(match)
        self.assertTrue(match["executed"])
        self.assertEqual(match["workflow_id"], "telegram-responder")
        self.assertEqual(match["output_message"], "Automated reply sent.")

    @patch("locallm.core.orchestrator.graph_executor.WorkflowGraphExecutor.run")
    def test_webhook_trigger_match(self, mock_run):
        """Verify HTTP webhook POST triggers active workflow with webhook-trigger."""
        mock_run.return_value = {
            "success": True,
            "steps_executed": 1,
            "state": {"context_variables": {}},
            "logs": [],
            "artifacts": [],
        }

        wf = {
            "id": "github-webhook-handler",
            "name": "GitHub CI Webhook",
            "isActive": True,
            "nodes": [
                {
                    "id": "w1",
                    "category": "triggers",
                    "tag": "webhook-trigger",
                    "title": "Webhook Receiver",
                    "properties": {
                        "inputs": {"path": "/github-event"},
                    },
                }
            ],
            "edges": [],
        }
        self.registry.save_workflow(wf)

        # Non-matching slug
        res = self.engine.match_and_trigger_webhook("gitlab-event", {"ref": "main"})
        self.assertIsNone(res)

        # Matching slug
        res = self.engine.match_and_trigger_webhook("github-event", {"ref": "main"})
        self.assertIsNotNone(res)
        self.assertTrue(res["executed"])
        self.assertEqual(res["workflow_id"], "github-webhook-handler")

    def test_schedule_and_messaging_trigger_execution_differentiation(self):
        """Verify graph executor distinguishes manual canvas test run from background daemon trigger."""
        from locallm.core.orchestrator.graph_executor import WorkflowGraphExecutor

        executor = WorkflowGraphExecutor()

        # 1. Schedule Trigger - Manual Canvas Test Run
        sched_node = {
            "id": "s1",
            "tag": "schedule-trigger",
            "title": "Daily Schedule",
            "properties": {"inputs": {"cron": "0 2 * * *", "query": "Nightly Security Audit"}},
        }
        res_manual = executor.run(nodes=[sched_node], edges=[], initial_state={})
        self.assertTrue(res_manual["success"])
        logs_manual = [l["message"] for l in res_manual["logs"]]
        self.assertTrue(any("[Manual Canvas Test Run] Schedule '0 2 * * *' bypassed" in m for m in logs_manual))

        # 2. Schedule Trigger - Live Scheduled Daemon Run
        res_daemon = executor.run(
            nodes=[sched_node],
            edges=[],
            initial_state={"context_variables": {"trigger_source": "schedule"}},
        )
        self.assertTrue(res_daemon["success"])
        logs_daemon = [l["message"] for l in res_daemon["logs"]]
        self.assertTrue(any("[Scheduled Cron Fired]" in m for m in logs_daemon))

        # 3. Messaging Trigger - Manual Canvas Test Run (Generic test query, zero Al-Kahfi)
        msg_node = {
            "id": "m1",
            "tag": "messaging-trigger",
            "title": "Telegram Inbound",
            "properties": {"options": {"platform": "telegram"}},
        }
        res_msg_manual = executor.run(nodes=[msg_node], edges=[], initial_state={})
        self.assertTrue(res_msg_manual["success"])
        logs_msg_manual = [l["message"] for l in res_msg_manual["logs"]]
        self.assertTrue(any("[Manual Canvas Test Run] Simulating TELEGRAM" in m for m in logs_msg_manual))
        self.assertNotIn("Al-Kahfi", str(res_msg_manual))

        # 4. Messaging Trigger - Live Real Chat Message
        res_msg_live = executor.run(
            nodes=[msg_node],
            edges=[],
            initial_state={
                "context_variables": {
                    "trigger_source": "telegram",
                    "inbound_message": "Deploy the staging environment now",
                    "sender": "lead_developer",
                }
            },
        )
        self.assertTrue(res_msg_live["success"])
        logs_msg_live = [l["message"] for l in res_msg_live["logs"]]
        self.assertTrue(any("[Live Inbound Message] Received real TELEGRAM message from lead_developer" in m for m in logs_msg_live))
        self.assertEqual(res_msg_live["state"]["objective"], "Deploy the staging environment now")


class TestWorkflowApiServerIntegration(unittest.TestCase):
    """Test API gateway HTTP endpoints for workflow CRUD, history, and execution."""

    @classmethod
    def setUpClass(cls):
        import http.client
        from locallm.config import LocaLLMConfig
        from locallm.modules.api_server import OpenAIAPIHandler, ThreadingOpenAIServer

        cls.config = LocaLLMConfig()
        cls.mock_client = MagicMock()
        cls.server = ThreadingOpenAIServer(
            server_address=("127.0.0.1", 0),
            RequestHandlerClass=OpenAIAPIHandler,
            config=cls.config,
            client=cls.mock_client,
            api_key="",
            workspace="default",
            is_background=True,
        )
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> tuple[int, dict]:
        import http.client
        import json

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json"} if body else {}
        body_bytes = json.dumps(body).encode("utf-8") if body else None
        conn.request(method, path, body=body_bytes, headers=headers)
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        conn.close()
        try:
            return res.status, json.loads(raw)
        except Exception:
            return res.status, {"raw": raw}

    def test_workflow_crud_and_toggle_api(self):
        """Verify GET, POST, toggle-active, and DELETE via HTTP."""
        # 1. GET /api/workflows
        status, data = self._request("GET", "/api/workflows")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

        # 2. POST /api/workflows (create)
        new_wf = {
            "id": "http-test-wf",
            "name": "HTTP Test Workflow",
            "isActive": False,
            "nodes": [{"id": "n1", "category": "triggers", "tag": "intake"}],
            "edges": [],
        }
        status, data = self._request("POST", "/api/workflows", new_wf)
        self.assertEqual(status, 200)
        self.assertEqual(data.get("id"), "http-test-wf")
        self.assertEqual(data.get("name"), "HTTP Test Workflow")

        # 3. GET /api/workflows/http-test-wf
        status, data = self._request("GET", "/api/workflows/http-test-wf")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("name"), "HTTP Test Workflow")

        # 4. POST /api/workflows/http-test-wf/toggle-active
        status, data = self._request("POST", "/api/workflows/http-test-wf/toggle-active")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("isActive"))

        # 5. GET /api/workflows/history
        status, data = self._request("GET", "/api/workflows/history")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

        # 6. DELETE /api/workflows/http-test-wf
        status, data = self._request("DELETE", "/api/workflows/http-test-wf")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))

    def test_webhook_api_trigger(self):
        """Verify POST /api/webhook/<slug> execution endpoint."""
        status, data = self._request("POST", "/api/webhook/some-test-slug", {"event": "ping"})
        self.assertEqual(status, 200)
        # Since no workflow is registered with slug 'some-test-slug', returns matched: False
        self.assertFalse(data.get("matched"))

    def test_workflow_run_stream_sse(self):
        """Verify POST /api/workflow/run-stream emits chunked SSE events."""
        import http.client
        import json

        wf_payload = {
            "nodes": [
                {
                    "id": "node-1",
                    "category": "triggers",
                    "tag": "intake",
                    "title": "User Objective Input",
                    "config": {"query": "Unit test objective"},
                },
                {
                    "id": "node-2",
                    "category": "outputs",
                    "tag": "chat-output",
                    "title": "Chat Output",
                    "config": {},
                },
            ],
            "edges": [{"from": "node-1", "to": "node-2"}],
            "workspace": "default",
            "execution_mode": "simulation",
        }

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        body = json.dumps(wf_payload).encode("utf-8")
        conn.request("POST", "/api/workflow/run-stream", body=body, headers={"Content-Type": "application/json"})
        res = conn.getresponse()
        self.assertEqual(res.status, 200)
        self.assertTrue((res.getheader("Content-Type") or "").startswith("text/event-stream"))

        raw_stream = res.read().decode("utf-8")
        conn.close()
        self.assertIn("node_progress", raw_stream)
        self.assertIn("completed", raw_stream)
        self.assertIn("node-1", raw_stream)

