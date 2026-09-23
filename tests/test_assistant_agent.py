"""Unit tests for multi-step ReAct agent loop in assistant module."""

import tempfile
from pathlib import Path
import unittest
from unittest.mock import MagicMock

from locallm.config import LocaLLMConfig
from locallm.core.memory import ConversationMemory
from locallm.core.workspace import get_all_available_skills, load_workspace_context
from locallm.modules.assistant import _process_assistant_turn


class TestAssistantMultiStepAgent(unittest.TestCase):
    """Test multi-step autonomous tool execution loop."""

    def test_multi_step_tool_calling_loop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            target_dir = tmp_path / "project_output"
            target_file = target_dir / "generated.py"

            config = LocaLLMConfig()
            config.agent_permission_policy = "always_allow"

            memory = ConversationMemory(system_prompt="Test agent")
            memory.add_user_message("Please scaffold the project and create generated.py")

            # Mock client simulating a 3-step sequence:
            # Step 1: create_directory
            # Step 2: write_file
            # Step 3: final answer summary
            client = MagicMock()
            step_turns = [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "create_directory",
                                "arguments": {"path": str(target_dir)},
                            },
                        }
                    ],
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_2",
                            "function": {
                                "name": "write_file",
                                "arguments": {
                                    "path": str(target_file),
                                    "content": "# Autonomous code\nprint('Done!')\n",
                                },
                            },
                        }
                    ],
                },
                {
                    "role": "assistant",
                    "content": "All project files and directories have been created successfully.",
                    "tool_calls": None,
                },
            ]
            client.chat_turn.side_effect = step_turns

            _process_assistant_turn(
                config=config,
                client=client,
                memory=memory,
                has_tools=True,
                model_name="mock-agent-model",
            )

            # Assert directory and file were actually created
            self.assertTrue(target_dir.exists())
            self.assertTrue(target_file.exists())
            self.assertIn("Autonomous code", target_file.read_text(encoding="utf-8"))

            # Assert conversation memory contains the final synthesis
            msgs = memory.get_messages()
            self.assertTrue(any("All project files and directories" in m.get("content", "") for m in msgs))

    def test_workspace_project_context_and_skills_discovery(self):
        ctx = load_workspace_context("default")
        # In current repo root, AGENTS.md exists
        self.assertIn("Project Architecture & Rules", ctx)
        self.assertIn("locaLLM", ctx)

        skills = get_all_available_skills("default")
        self.assertIsInstance(skills, list)

    def test_ignorance_refusal_interceptor_triggers_search_web(self):
        config = LocaLLMConfig()
        memory = ConversationMemory(system_prompt="Test assistant")
        user_query = "Cari informasi terkait goldengate delinea"
        memory.add_user_message(user_query)

        # Mock client simulating:
        # Step 1: Ignorant refusal response (text only)
        # Step 2: Nudge intercepted -> Model invokes search_web
        # Step 3: Model final synthesis
        client = MagicMock()
        step_turns = [
            {
                "role": "assistant",
                "content": "I do not have information about goldengate delinea in my pre-trained data.",
                "tool_calls": [],
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_search_1",
                        "function": {
                            "name": "search_web",
                            "arguments": {"query": "goldengate delinea"},
                        },
                    }
                ],
            },
            {
                "role": "assistant",
                "content": "Delinea GoldenGate is a privileged access management integration for databases.",
                "tool_calls": [],
            },
        ]
        client.chat_turn.side_effect = step_turns

        # Mock execute_tool to avoid live HTTP call during unit test
        with unittest.mock.patch("locallm.modules.assistant.execute_tool", return_value="[Search Results: Delinea integration with GoldenGate]"):
            _process_assistant_turn(
                config=config,
                client=client,
                memory=memory,
                has_tools=True,
                model_name="mock-model",
            )

        msgs = memory.get_messages()
        self.assertTrue(any("Delinea GoldenGate is a privileged access management" in m.get("content", "") for m in msgs))
        # Ensure client was called 3 times (refusal -> nudge -> final synthesis)
        self.assertEqual(client.chat_turn.call_count, 3)


if __name__ == "__main__":
    unittest.main()
