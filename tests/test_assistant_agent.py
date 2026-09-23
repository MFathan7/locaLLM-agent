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

    def test_react_agent_unified_tool_execution(self):
        """Test ReActAgent executes native tools via unified execute_tool dispatcher."""
        from locallm.modules.agent import AgentEngine

        config = LocaLLMConfig()
        config.agent_permission_policy = "always_allow"
        client = MagicMock()

        # Step 1: Model calls fetch_web
        # Step 2: Model outputs final answer
        client.chat_turn.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "fetch_web",
                            "arguments": {"url": "https://github.com/ollama/ollama/releases"},
                        },
                    }
                ],
            },
            {
                "role": "assistant",
                "content": "Task completed: Ollama releases were verified successfully.",
                "tool_calls": None,
            },
        ]

        with unittest.mock.patch("locallm.modules.agent.execute_tool", return_value="Latest Release: v0.5.12") as mock_exec:
            agent = AgentEngine(config, client, model_name="test-model", max_steps=10, interactive=False)
            agent.run_task("Fetch Ollama releases")

            # Verify execute_tool was called with fetch_web
            mock_exec.assert_called_once()
            args, kwargs = mock_exec.call_args
            self.assertEqual(args[0], "fetch_web")
            self.assertEqual(args[1], {"url": "https://github.com/ollama/ollama/releases"})

    def test_fetch_web_github_releases_api(self):
        """Test fetch_web parses GitHub releases API and formats clean summary."""
        from locallm.core.tools import execute_tool

        mock_releases = [
            {
                "tag_name": "v0.5.12",
                "name": "Ollama 0.5.12",
                "published_at": "2025-02-15T10:00:00Z",
                "prerelease": False,
                "body": "Fixes and performance improvements for local inference.",
            },
            {
                "tag_name": "v0.5.11",
                "name": "Ollama 0.5.11",
                "published_at": "2025-02-10T09:00:00Z",
                "prerelease": False,
                "body": "Added new model support.",
            },
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_releases

        with unittest.mock.patch("httpx.Client.get", return_value=mock_resp):
            result = execute_tool("fetch_web", {"url": "https://github.com/ollama/ollama/releases"})

            self.assertIn("v0.5.12", result)
            self.assertIn("Ollama 0.5.12", result)
            self.assertIn("GitHub Releases for ollama/ollama", result)
            self.assertIn("v0.5.11", result)

    def test_react_agent_step_limit_synthesis(self):
        """Test ReActAgent synthesizes final summary when step limit is reached in non-interactive mode."""
        from locallm.modules.agent import AgentEngine

        config = LocaLLMConfig()
        client = MagicMock()

        # Model loops continuously emitting tools
        client.chat_turn.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": f"call_{i}",
                        "function": {
                            "name": "get_current_time",
                            "arguments": {},
                        },
                    }
                ],
            }
            for i in range(5)
        ] + [
            # Final synthesis turn response
            {
                "role": "assistant",
                "content": "Final synthesis: collected observations before step limit.",
                "tool_calls": None,
            }
        ]

        agent = AgentEngine(config, client, max_steps=2, interactive=False)
        agent.run_task("Loop test")

        # chat_turn called for step 1, step 2, and the final synthesis turn
        self.assertEqual(client.chat_turn.call_count, 3)

    def test_fetch_web_github_repo_api(self):
        """Test fetch_web parses GitHub repo API and returns compact summary."""
        from locallm.core.tools import execute_tool

        mock_data = {
            "full_name": "golang/go",
            "description": "The Go programming language",
            "stargazers_count": 125000,
            "forks_count": 18000,
            "open_issues_count": 9200,
            "license": {"name": "BSD-3-Clause"},
            "language": "Go",
            "created_at": "2014-06-24T18:05:46Z",
            "updated_at": "2026-09-23T06:00:00Z",
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data

        with unittest.mock.patch("httpx.Client.get", return_value=mock_resp):
            result = execute_tool("fetch_web", {"url": "https://api.github.com/repos/golang/go"})

            self.assertIn("GitHub Repository Data for golang/go", result)
            self.assertIn("125000", result)
            self.assertIn("BSD-3-Clause", result)
            self.assertIn("9200", result)

    def test_agent_graceful_timeout_with_executed_actions(self):
        """Test agent gracefully handles model timeout/error when tools were already executed."""
        from locallm.modules.agent import AgentEngine

        config = LocaLLMConfig()
        client = MagicMock()

        # Step 1: Model calls write_file
        # Step 2: Model times out (raises Exception)
        client.chat_turn.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "get_current_time",
                            "arguments": {},
                        },
                    }
                ],
            },
            Exception("timed out"),
        ]

        agent = AgentEngine(config, client, max_steps=5, interactive=False)
        # Should not raise exception
        try:
            agent.run_task("Task that times out after step 1")
        except Exception as exc:
            self.fail(f"agent.run_task raised an unexpected exception: {exc}")


if __name__ == "__main__":
    unittest.main()


