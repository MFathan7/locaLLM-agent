"""Unit tests for Smart Task Termination, Early Exit Logic, and complete_task tool."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from locallm.config import LocaLLMConfig
from locallm.core.memory import ConversationMemory
from locallm.core.tools import ASSISTANT_TOOLS, registry, execute_tool
from locallm.modules.agent import ReActAgent
from locallm.modules.assistant import _process_assistant_turn


class TestSmartTermination(unittest.TestCase):
    """Test suite for smart task termination and early exit mechanisms."""

    def test_complete_task_tool_registration_and_schema(self):
        """Verify complete_task is properly registered in tool registry and ASSISTANT_TOOLS."""
        tool_obj = registry.get("complete_task")
        self.assertIsNotNone(tool_obj)
        self.assertFalse(tool_obj.is_mutating)

        schema = tool_obj.to_schema()
        self.assertEqual(schema["function"]["name"], "complete_task")
        self.assertIn("final_answer", schema["function"]["parameters"]["properties"])
        self.assertIn("final_answer", schema["function"]["parameters"]["required"])

        # Check execution function
        res = execute_tool("complete_task", {"final_answer": "All tasks done."})
        self.assertEqual(res, "All tasks done.")

        # Check presence in global ASSISTANT_TOOLS
        names = [t.get("function", {}).get("name") for t in ASSISTANT_TOOLS]
        self.assertIn("complete_task", names)

    def test_agent_early_exit_on_text_only_response(self):
        """Kondisi 1: Agent must exit immediately when model returns text without tool calls."""
        config = LocaLLMConfig()
        config.agent_permission_policy = "always_allow"

        client = MagicMock()
        client.chat_turn.return_value = {
            "role": "assistant",
            "content": "The answer is 42.",
            "tool_calls": None,
        }

        agent = ReActAgent(config, client, max_steps=50, interactive=False)
        agent.run_task("What is the meaning of life?")

        # Must execute only 1 turn and exit immediately
        self.assertEqual(client.chat_turn.call_count, 1)

    def test_agent_early_exit_on_complete_task_call(self):
        """Kondisi 2: Agent must exit immediately upon encountering complete_task tool call."""
        config = LocaLLMConfig()
        config.agent_permission_policy = "always_allow"

        client = MagicMock()
        step_turns = [
            # Turn 1: model executes complete_task
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_comp_1",
                        "function": {
                            "name": "complete_task",
                            "arguments": json.dumps({"final_answer": "Analysis complete. System is stable."}),
                        },
                    }
                ],
            },
            # Turn 2: should never be reached
            {
                "role": "assistant",
                "content": "Should not be called",
                "tool_calls": None,
            },
        ]
        client.chat_turn.side_effect = step_turns

        agent = ReActAgent(config, client, max_steps=50, interactive=False)
        agent.run_task("Audit system status")

        # Must terminate after turn 1 without executing further steps
        self.assertEqual(client.chat_turn.call_count, 1)

    def test_agent_progressive_soft_limit_nudge(self):
        """Kondisi 3: Agent must inject dynamic system warning when reaching soft limit threshold."""
        config = LocaLLMConfig()
        config.agent_permission_policy = "always_allow"

        client = MagicMock()
        # Mock 10 consecutive tool calls of list_directory followed by final answer
        calls = []
        for i in range(12):
            calls.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": f"call_{i}",
                        "function": {
                            "name": "get_current_directory",
                            "arguments": {},
                        },
                    }
                ],
            })
        calls.append({
            "role": "assistant",
            "content": "Done after steps.",
            "tool_calls": None,
        })
        client.chat_turn.side_effect = calls

        agent = ReActAgent(config, client, max_steps=20, interactive=False)
        agent.run_task("Inspect files")

        # Check call arguments across invocations: at soft limit step (8), a system warning should be injected
        history_at_soft_limit = client.chat_turn.call_args_list[8][1]["messages"]
        nudge_found = any(
            "Observation budget is almost exhausted" in m.get("content", "")
            for m in history_at_soft_limit
        )
        self.assertTrue(nudge_found, "Progressive nudge was not found in message history at soft limit")

    def test_assistant_early_exit_on_complete_task(self):
        """Kondisi 2 in Assistant: _process_assistant_turn must terminate immediately on complete_task."""
        config = LocaLLMConfig()
        memory = ConversationMemory(system_prompt="Test assistant")
        memory.add_user_message("Create report and finish")

        client = MagicMock()
        client.chat_turn.return_value = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "asst_comp_1",
                    "function": {
                        "name": "complete_task",
                        "arguments": {"final_answer": "Report created and verified."},
                    },
                }
            ],
        }

        _process_assistant_turn(
            config=config,
            client=client,
            memory=memory,
            has_tools=True,
            model_name="mock-model",
        )

        self.assertEqual(client.chat_turn.call_count, 1)
        msgs = memory.get_messages()
        self.assertTrue(any("Report created and verified" in m.get("content", "") for m in msgs))


if __name__ == "__main__":
    unittest.main()
