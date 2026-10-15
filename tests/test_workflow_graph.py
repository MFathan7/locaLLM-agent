"""Unit tests for WorkflowGraphExecutor (n8n + Multi-Agent Coordinator engine)."""

import unittest
from unittest.mock import MagicMock
from locallm.config import LocaLLMConfig
from locallm.core.orchestrator.graph_executor import WorkflowGraphExecutor


class TestWorkflowGraphExecutor(unittest.TestCase):
    """Test 2-port topology execution, sub-node resolution, and Quality Gate loops."""

    def setUp(self):
        self.config = LocaLLMConfig()
        self.mock_client = MagicMock()
        self.executor = WorkflowGraphExecutor(self.config, self.mock_client)

    def test_linear_main_flow_execution(self):
        """Verify linear main flow execution from User Intake to Output."""
        nodes = [
            {
                "id": "node-1",
                "category": "triggers",
                "tag": "intake",
                "title": "User Objective Input",
                "config": {"query": "Test unit goal"},
            },
            {
                "id": "node-2",
                "category": "orchestration",
                "tag": "supervisor",
                "title": "Supervisor Coordinator",
                "config": {"directive": "Plan tasks"},
            },
            {
                "id": "node-3",
                "category": "outputs",
                "tag": "chat-output",
                "title": "Chat Output",
                "config": {},
            },
        ]
        edges = [
            {"id": "e1", "from": "node-1", "to": "node-2", "fromSide": "right", "toSide": "left"},
            {"id": "e2", "from": "node-2", "to": "node-3", "fromSide": "right", "toSide": "left"},
        ]

        result = self.executor.run(nodes, edges, workspace_name="default", execution_mode="simulation")
        self.assertTrue(result["success"])
        self.assertEqual(result["steps_executed"], 3)
        self.assertEqual(result["state"]["objective"], "Test unit goal")
        self.assertEqual(result["state"]["status"], "success")

    def test_sub_node_tool_and_router_resolution(self):
        """Verify sub-node plugged into bottom port injects tools and model into supervisor."""
        nodes = [
            {
                "id": "supervisor",
                "category": "orchestration",
                "tag": "supervisor",
                "title": "Supervisor Coordinator",
                "config": {},
            },
            {
                "id": "model-router",
                "category": "orchestration",
                "tag": "model-router",
                "title": "Dynamic Model Router",
                "config": {},
            },
            {
                "id": "tool-shell",
                "category": "tools_plugins",
                "tag": "subprocess",
                "title": "Shell Runner",
                "config": {"command": "pytest -q"},
            },
        ]
        edges = [
            # Sub-node connections pointing from top of sub-node into bottom of supervisor
            {"id": "se1", "from": "model-router", "to": "supervisor", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
            {"id": "se2", "from": "tool-shell", "to": "supervisor", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
        ]

        sub_nodes = self.executor._resolve_sub_nodes("supervisor", nodes, edges)
        self.assertEqual(len(sub_nodes), 2)
        plugged_tools = self.executor._resolve_plugged_tools(nodes[0], sub_nodes)
        self.assertIn("execute_command", plugged_tools)

    def test_quality_gate_retry_loop(self):
        """Verify Quality Gate loops back on failed Critic score until cleared."""
        nodes = [
            {
                "id": "intake",
                "category": "triggers",
                "tag": "intake",
                "title": "User Objective Input",
                "config": {"query": "Refactor module"},
            },
            {
                "id": "coder",
                "category": "specialists",
                "tag": "coder",
                "title": "Coder Agent",
                "config": {},
            },
            {
                "id": "critic",
                "category": "specialists",
                "tag": "critic",
                "title": "Critic QA Agent",
                "config": {},
            },
            {
                "id": "gate",
                "category": "flow_control",
                "tag": "quality-gate",
                "title": "Quality Gate",
                "config": {"max_retries": 1},
            },
            {
                "id": "output",
                "category": "outputs",
                "tag": "chat-output",
                "title": "Chat Output",
                "config": {},
            },
        ]
        edges = [
            {"id": "e1", "from": "intake", "to": "coder", "fromSide": "right", "toSide": "left"},
            {"id": "e2", "from": "coder", "to": "critic", "fromSide": "right", "toSide": "left"},
            {"id": "e3", "from": "critic", "to": "gate", "fromSide": "right", "toSide": "left"},
            {"id": "e4", "from": "gate", "to": "coder", "fromSide": "right", "toSide": "left", "label": "loop revision", "conditionBranch": "loop"},
            {"id": "e5", "from": "gate", "to": "output", "fromSide": "right", "toSide": "left", "label": "pass approved", "conditionBranch": "true"},
        ]

        result = self.executor.run(nodes, edges, workspace_name="default", execution_mode="simulation")
        self.assertTrue(result["success"])
        # Should have executed coder, critic, gate, and finally output
        self.assertGreaterEqual(result["steps_executed"], 4)
        self.assertTrue(result["state"]["verdict"]["passed"])

    def test_preset_a_code_audit_graph_execution(self):
        """Verify Preset A (Full-Stack Code Audit & Auto-Refactor) runs cleanly end-to-end."""
        nodes = [
            {"id": "audit-intake", "category": "triggers", "tag": "intake", "title": "User Objective Input", "config": {"query": "Audit repository"}},
            {"id": "audit-decomposer", "category": "orchestration", "tag": "task-decomposer", "title": "Task Decomposer", "config": {"max_subtasks": 3}},
            {"id": "audit-supervisor", "category": "orchestration", "tag": "supervisor", "title": "Supervisor Coordinator", "config": {"directive": "Coordinate audit"}},
            {"id": "audit-critic", "category": "specialists", "tag": "critic", "title": "Critic / QA Agent", "config": {"pass_threshold": 85}},
            {"id": "audit-gate", "category": "flow_control", "tag": "quality-gate", "title": "Quality Gate", "config": {"max_retries": 3, "min_score": 85}},
            {"id": "audit-output", "category": "outputs", "tag": "chat-output", "title": "Chat & Artifact Output", "config": {}},
            {"id": "audit-router", "category": "orchestration", "tag": "model-router", "title": "Dynamic Model Router", "config": {"fast_model": "gemma4:12b"}},
            {"id": "audit-blackboard", "category": "state_knowledge", "tag": "blackboard", "title": "Blackboard Hub", "config": {}},
            {"id": "audit-coder", "category": "specialists", "tag": "coder", "title": "Coder Agent", "config": {"tools": ["patch_file", "write_file"]}},
            {"id": "audit-fs", "category": "tools_plugins", "tag": "filesystem", "title": "Filesystem", "config": {"path": "."}},
            {"id": "audit-shell", "category": "tools_plugins", "tag": "subprocess", "title": "Shell Runner", "config": {"command": "pytest -q"}},
        ]
        edges = [
            {"id": "ae-main-1", "from": "audit-intake", "to": "audit-decomposer", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "ae-main-2", "from": "audit-decomposer", "to": "audit-supervisor", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "ae-main-3", "from": "audit-supervisor", "to": "audit-critic", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "ae-main-4", "from": "audit-critic", "to": "audit-gate", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "ae-gate-pass", "from": "audit-gate", "to": "audit-output", "fromSide": "right", "toSide": "left", "kind": "conditional", "conditionBranch": "true"},
            {"id": "ae-gate-loop", "from": "audit-gate", "to": "audit-supervisor", "fromSide": "left", "toSide": "bottom", "kind": "conditional", "conditionBranch": "loop"},
            {"id": "ae-sub-router", "from": "audit-router", "to": "audit-supervisor", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
            {"id": "ae-sub-blackboard", "from": "audit-blackboard", "to": "audit-supervisor", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
            {"id": "ae-sub-coder", "from": "audit-coder", "to": "audit-supervisor", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
            {"id": "ae-sub-fs", "from": "audit-fs", "to": "audit-coder", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
            {"id": "ae-sub-shell", "from": "audit-shell", "to": "audit-coder", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
        ]

        result = self.executor.run(nodes, edges, workspace_name="default", execution_mode="simulation")
        self.assertTrue(result["success"])
        self.assertEqual(result["state"]["objective"], "Audit repository")
        self.assertGreaterEqual(result["steps_executed"], 6)

    def test_preset_b_deep_tech_intelligence_graph_execution(self):
        """Verify Preset B (Deep Tech & Market Intelligence Report) runs cleanly end-to-end."""
        nodes = [
            {"id": "intel-intake", "category": "triggers", "tag": "intake", "title": "User Objective Input", "config": {"query": "Analyze local LLM market"}},
            {"id": "intel-supervisor", "category": "orchestration", "tag": "supervisor", "title": "Supervisor Coordinator", "config": {"directive": "Gather intel"}},
            {"id": "intel-aggregator", "category": "orchestration", "tag": "parallel-aggregator", "title": "Parallel Aggregator", "config": {}},
            {"id": "intel-writer", "category": "specialists", "tag": "writer", "title": "Writer Agent", "config": {}},
            {"id": "intel-doc-exporter", "category": "outputs", "tag": "doc-exporter", "title": "Document Exporter", "config": {}},
            {"id": "intel-chat-output", "category": "outputs", "tag": "chat-output", "title": "Chat Output", "config": {}},
            {"id": "intel-router", "category": "orchestration", "tag": "model-router", "title": "Dynamic Model Router", "config": {}},
            {"id": "intel-blackboard", "category": "state_knowledge", "tag": "blackboard", "title": "Blackboard Hub", "config": {}},
            {"id": "intel-researcher", "category": "specialists", "tag": "researcher", "title": "Researcher Agent", "config": {}},
            {"id": "intel-web-search", "category": "tools_plugins", "tag": "online-web", "title": "Web Search", "config": {}},
            {"id": "intel-rag", "category": "state_knowledge", "tag": "rag-retriever", "title": "RAG Retriever", "config": {}},
        ]
        edges = [
            {"id": "be-main-1", "from": "intel-intake", "to": "intel-supervisor", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "be-main-2", "from": "intel-supervisor", "to": "intel-aggregator", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "be-main-3", "from": "intel-aggregator", "to": "intel-writer", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "be-main-4", "from": "intel-writer", "to": "intel-doc-exporter", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "be-main-5", "from": "intel-writer", "to": "intel-chat-output", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "be-sub-router", "from": "intel-router", "to": "intel-supervisor", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
            {"id": "be-sub-blackboard", "from": "intel-blackboard", "to": "intel-supervisor", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
            {"id": "be-sub-researcher", "from": "intel-researcher", "to": "intel-supervisor", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
            {"id": "be-sub-search", "from": "intel-web-search", "to": "intel-researcher", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
            {"id": "be-sub-rag", "from": "intel-rag", "to": "intel-supervisor", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
        ]

        result = self.executor.run(nodes, edges, workspace_name="default", execution_mode="simulation")
        self.assertTrue(result["success"])
        self.assertEqual(result["state"]["objective"], "Analyze local LLM market")
        self.assertGreaterEqual(result["steps_executed"], 5)

    def test_preset_c_automated_ops_messaging_graph_execution(self):
        """Verify Preset C (Automated Ops & DB Assistant via Messaging) runs cleanly end-to-end."""
        nodes = [
            {"id": "ops-trigger", "category": "triggers", "tag": "messaging-trigger", "title": "Messaging Trigger", "config": {"platform": "telegram"}},
            {"id": "ops-intent", "category": "orchestration", "tag": "intent-switch", "title": "Semantic Intent Switch", "config": {"branches": ["DATA_QUERY", "OPS_COMPLEX"]}},
            {"id": "ops-data-analyst", "category": "specialists", "tag": "data-analyst", "title": "Data/DB Analyst", "config": {"query": "SELECT 1"}},
            {"id": "ops-plugin-exec", "category": "tools_plugins", "tag": "plugin-executor", "title": "Plugin Executor", "config": {}},
            {"id": "ops-supervisor", "category": "orchestration", "tag": "supervisor", "title": "Supervisor Coordinator", "config": {"directive": "Execute ops"}},
            {"id": "ops-memory", "category": "state_knowledge", "tag": "memory-rw", "title": "Memory R/W", "config": {}},
            {"id": "ops-web-search", "category": "tools_plugins", "tag": "online-web", "title": "Web Search", "config": {}},
            {"id": "ops-approval", "category": "flow_control", "tag": "policy-gate", "title": "Human Approval", "config": {}},
            {"id": "ops-dispatcher", "category": "outputs", "tag": "messaging-dispatcher", "title": "Messaging Dispatcher", "config": {}},
        ]
        edges = [
            {"id": "ce-main-trigger", "from": "ops-trigger", "to": "ops-intent", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "ce-branch-db", "from": "ops-intent", "to": "ops-data-analyst", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "ce-branch-ops", "from": "ops-intent", "to": "ops-supervisor", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "ce-db-output", "from": "ops-data-analyst", "to": "ops-dispatcher", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "ce-ops-approval", "from": "ops-supervisor", "to": "ops-approval", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "ce-approval-output", "from": "ops-approval", "to": "ops-dispatcher", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "ce-sub-plugin", "from": "ops-plugin-exec", "to": "ops-data-analyst", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
            {"id": "ce-sub-memory", "from": "ops-memory", "to": "ops-supervisor", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
            {"id": "ce-sub-search", "from": "ops-web-search", "to": "ops-supervisor", "fromSide": "top", "toSide": "bottom", "kind": "sub"},
        ]

        result = self.executor.run(nodes, edges, workspace_name="default", execution_mode="simulation")
        self.assertTrue(result["success"])
        self.assertGreaterEqual(result["steps_executed"], 4)



if __name__ == "__main__":
    unittest.main()
