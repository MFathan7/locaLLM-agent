"""Unit tests for WorkflowGraphExecutor (DAG & Multi-Agent Coordinator engine)."""

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

    def test_dynamic_properties_and_runtime_interpolation(self):
        """Verify dynamic properties resolution and {{variable}} / {{node.output}} interpolation."""
        nodes = [
            {
                "id": "node-intake",
                "category": "triggers",
                "tag": "intake",
                "title": "User Objective Input",
                "properties": {
                    "common": {
                        "displayName": "Intake Trigger",
                        "description": "Receives user request",
                        "continueOnError": False,
                        "timeoutSeconds": 30,
                    },
                    "inputs": {
                        "query": "Autonomous Agent Architecture",
                    },
                    "options": {
                        "mode": "standard",
                    },
                    "output": {
                        "outputVariable": "user_objective",
                    },
                },
            },
            {
                "id": "node-researcher",
                "category": "specialists",
                "tag": "researcher",
                "title": "Deep Researcher Agent",
                "properties": {
                    "common": {
                        "displayName": "Deep Researcher",
                        "description": "Conducts deep analysis",
                        "continueOnError": False,
                        "timeoutSeconds": 60,
                    },
                    "inputs": {
                        "searchQuery": "{{user_objective}} best practices",
                        "systemPrompt": "Analyze topic: {{node-intake.output.query}}",
                    },
                    "options": {
                        "model": "deepseek-r1:8b",
                        "temperature": 0.4,
                    },
                    "output": {
                        "outputVariable": "out_research_data",
                    },
                },
            },
            {
                "id": "node-dispatcher",
                "category": "outputs",
                "tag": "messaging-dispatcher",
                "title": "Messaging Dispatcher",
                "properties": {
                    "common": {
                        "displayName": "Telegram Alert",
                        "continueOnError": False,
                        "timeoutSeconds": 15,
                    },
                    "inputs": {
                        "recipient": "@engineering_lead",
                        "messageTemplate": "Report for {{user_objective}}: Summary -> {{out_research_data.summary}}",
                    },
                    "options": {
                        "channel": "slack",
                    },
                    "output": {
                        "outputVariable": "out_notification",
                    },
                },
            },
        ]
        edges = [
            {"id": "e-dyn-1", "from": "node-intake", "to": "node-researcher", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "e-dyn-2", "from": "node-researcher", "to": "node-dispatcher", "fromSide": "right", "toSide": "left", "kind": "main"},
        ]

        result = self.executor.run(nodes, edges, workspace_name="default", execution_mode="simulation")
        self.assertTrue(result["success"])
        self.assertEqual(result["steps_executed"], 3)

        context_vars = result["state"]["context_variables"]
        # Verify custom outputVariable binding
        self.assertIn("user_objective", context_vars)
        self.assertIn("out_research_data", context_vars)
        self.assertIn("out_notification", context_vars)

        # Verify default node_id.output binding
        self.assertIn("node-intake.output", context_vars)
        self.assertIn("node-researcher.output", context_vars)

        # Verify variable interpolation in downstream dispatcher message
        dispatch_result = context_vars["out_notification"]
        self.assertIn("Report for Autonomous Agent Architecture:", dispatch_result["message"])
        self.assertIn("Summary ->", dispatch_result["message"])

    def test_continue_on_error_flag_handling(self):
        """Verify continueOnError allows workflow to proceed despite a node failure."""
        class FailingExecutor(WorkflowGraphExecutor):
            def _execute_single_node(self, *args, **kwargs):
                node = args[0] if args else kwargs.get("node", {})
                if isinstance(node, dict) and node.get("id") == "fail-node":
                    raise RuntimeError("Simulated failure in test step")
                return super()._execute_single_node(*args, **kwargs)

        failing_executor = FailingExecutor(self.config, self.mock_client)

        nodes_strict = [
            {
                "id": "node-start",
                "category": "triggers",
                "tag": "intake",
                "title": "Start Node",
                "properties": {"common": {"continueOnError": False}, "inputs": {"query": "Task"}, "options": {}, "output": {}},
            },
            {
                "id": "fail-node",
                "category": "specialists",
                "tag": "coder",
                "title": "Coder Step",
                "properties": {"common": {"continueOnError": False}, "inputs": {}, "options": {}, "output": {}},
            },
            {
                "id": "node-end",
                "category": "outputs",
                "tag": "chat-output",
                "title": "End Node",
                "properties": {"common": {"continueOnError": False}, "inputs": {}, "options": {}, "output": {}},
            },
        ]
        edges = [
            {"id": "ef-1", "from": "node-start", "to": "fail-node", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "ef-2", "from": "fail-node", "to": "node-end", "fromSide": "right", "toSide": "left", "kind": "main"},
        ]

        # 1. With continueOnError = False, workflow should halt with success = False
        res_fail = failing_executor.run(nodes_strict, edges, workspace_name="default", execution_mode="simulation")
        self.assertFalse(res_fail["success"])
        self.assertIn("Simulated failure in test step", res_fail.get("error", ""))

        # 2. With continueOnError = True on fail-node, workflow should complete end-to-end
        nodes_lenient = [
            nodes_strict[0],
            {
                "id": "fail-node",
                "category": "specialists",
                "tag": "coder",
                "title": "Coder Step",
                "properties": {"common": {"continueOnError": True}, "inputs": {}, "options": {}, "output": {}},
            },
            nodes_strict[2],
        ]
        res_ok = failing_executor.run(nodes_lenient, edges, workspace_name="default", execution_mode="simulation")
        self.assertTrue(res_ok["success"])
        self.assertEqual(res_ok["steps_executed"], 3)

    def test_property_schema_and_interpolation_helpers(self):
        """Test recursive property interpolation and default property generation helpers."""
        from locallm.core.orchestrator.property_schema import (
            get_default_properties_for_tag,
            interpolate_properties,
            ensure_node_dynamic_properties,
        )

        props = get_default_properties_for_tag("researcher")
        self.assertIn("common", props)
        self.assertIn("inputs", props)
        self.assertIn("options", props)
        self.assertIn("output", props)
        self.assertEqual(props["output"]["outputVariable"], "out_research_data")

        # Test interpolation with nested dicts and fallback
        template_props = {
            "inputs": {
                "prompt": "Hello {{user.name}}, your score is {{stats.score}}",
                "unresolved": "{{unknown_var}}",
            },
            "options": {
                "maxRetries": 3,
                "enabled": True,
            },
        }
        ctx = {
            "user": {"name": "Alex"},
            "stats": {"score": 98.5},
        }
        resolved = interpolate_properties(template_props, ctx)
        self.assertEqual(resolved["inputs"]["prompt"], "Hello Alex, your score is 98.5")
        self.assertEqual(resolved["inputs"]["unresolved"], "{{unknown_var}}")
        self.assertEqual(resolved["options"]["maxRetries"], 3)
        self.assertTrue(resolved["options"]["enabled"])

        # Test legacy node fallback migration
        legacy_node = {
            "id": "legacy-1",
            "tag": "online-web",
            "category": "tools_plugins",
            "title": "Legacy Search",
            "config": {"query": "climate change"},
        }
        migrated = ensure_node_dynamic_properties(legacy_node)
        self.assertIn("properties", migrated)
        self.assertEqual(migrated["properties"]["inputs"]["query"], "climate change")

    def test_zero_variable_implicit_data_flow(self):
        """Verify seamless zero-variable data passing where edge connections implicitly transfer data."""
        nodes = [
            {
                "id": "start-node",
                "category": "triggers",
                "tag": "intake",
                "title": "Start Trigger",
                "properties": {
                    "common": {"displayName": "User Request"},
                    "inputs": {"query": "Implicit Flow Optimization"},
                    "options": {"parameterMode": "custom"},
                    "output": {},
                },
            },
            {
                "id": "research-step",
                "category": "specialists",
                "tag": "researcher",
                "title": "Autonomous Researcher",
                "properties": {
                    "common": {"displayName": "Auto Research"},
                    "inputs": {},  # Completely empty - ZERO variables
                    "options": {"parameterMode": "auto"},
                    "output": {},
                },
            },
            {
                "id": "dispatch-step",
                "category": "outputs",
                "tag": "messaging-dispatcher",
                "title": "Notification Dispatcher",
                "properties": {
                    "common": {"displayName": "Auto Dispatch"},
                    "inputs": {},  # Completely empty - ZERO variables
                    "options": {"parameterMode": "auto", "channel": "slack"},
                    "output": {},
                },
            },
        ]
        edges = [
            {"id": "e-auto-1", "from": "start-node", "to": "research-step", "fromSide": "right", "toSide": "left", "kind": "main"},
            {"id": "e-auto-2", "from": "research-step", "to": "dispatch-step", "fromSide": "right", "toSide": "left", "kind": "main"},
        ]

        result = self.executor.run(nodes, edges, workspace_name="default", execution_mode="simulation")
        self.assertTrue(result["success"])
        self.assertEqual(result["steps_executed"], 3)

        # Confirm research step automatically picked up the objective from predecessor
        research_out = result["state"]["context_variables"].get("research-step.output")
        self.assertIsNotNone(research_out)
        self.assertEqual(research_out["query"], "Implicit Flow Optimization")

        # Confirm dispatcher automatically incorporated upstream context
        dispatch_out = result["state"]["context_variables"].get("dispatch-step.output")
        self.assertIsNotNone(dispatch_out)
        self.assertIn("Implicit Flow Optimization", dispatch_out["message"])

    def test_multi_predecessor_context_merging(self):
        """Verify multiple predecessor nodes entering one node merge their outputs cleanly."""
        nodes = [
            {
                "id": "trigger-node",
                "category": "triggers",
                "tag": "intake",
                "title": "Intake",
                "properties": {"inputs": {"query": "Multi-agent audit"}, "options": {}},
            },
            {
                "id": "spec-research",
                "category": "specialists",
                "tag": "researcher",
                "title": "Market Analyst",
                "properties": {"options": {"parameterMode": "auto"}},
            },
            {
                "id": "spec-coder",
                "category": "specialists",
                "tag": "coder",
                "title": "Code Specialist",
                "properties": {"options": {"parameterMode": "auto"}},
            },
            {
                "id": "merge-output",
                "category": "outputs",
                "tag": "messaging-dispatcher",
                "title": "Final Broadcaster",
                "properties": {"options": {"parameterMode": "auto", "channel": "slack"}},
            },
        ]
        edges = [
            {"id": "em-1", "from": "trigger-node", "to": "spec-research", "kind": "main"},
            {"id": "em-2", "from": "trigger-node", "to": "spec-coder", "kind": "main"},
            {"id": "em-3", "from": "spec-research", "to": "merge-output", "kind": "main"},
            {"id": "em-4", "from": "spec-coder", "to": "merge-output", "kind": "main"},
        ]

        result = self.executor.run(nodes, edges, workspace_name="default", execution_mode="simulation")
        self.assertTrue(result["success"])
        self.assertGreaterEqual(result["steps_executed"], 4)

        # Check final broadcaster output message contains merged context
        dispatch_out = result["state"]["context_variables"].get("merge-output.output")
        self.assertIsNotNone(dispatch_out)
        self.assertIn("Multi-agent audit", dispatch_out["message"])

    def test_auto_vs_custom_parameter_mode_override(self):
        """Verify parameterMode = 'custom' prioritizes user inputs over automated defaults."""
        nodes = [
            {
                "id": "trigger",
                "category": "triggers",
                "tag": "intake",
                "title": "Trigger",
                "properties": {"inputs": {"query": "Default Objective"}, "options": {}},
            },
            {
                "id": "custom-research",
                "category": "specialists",
                "tag": "researcher",
                "title": "Custom Analyst",
                "properties": {
                    "inputs": {"searchQuery": "Specific Custom Prompt Override"},
                    "options": {"parameterMode": "custom"},
                },
            },
        ]
        edges = [
            {"id": "ec-1", "from": "trigger", "to": "custom-research", "kind": "main"},
        ]

        result = self.executor.run(nodes, edges, workspace_name="default", execution_mode="simulation")
        self.assertTrue(result["success"])
        custom_out = result["state"]["context_variables"].get("custom-research.output")
        self.assertEqual(custom_out["query"], "Specific Custom Prompt Override")


if __name__ == "__main__":
    unittest.main()


