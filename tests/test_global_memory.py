"""Tests for Global Memory Manager, memory tool, context injection, and cross-workspace isolation."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from locallm.core.global_memory import GlobalMemoryManager
from locallm.core.tools import execute_tool, get_all_assistant_tools


class TestGlobalMemory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.memory_file = self.temp_dir / "global_memory.json"
        self.manager = GlobalMemoryManager(storage_path=str(self.memory_file))

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization_creates_file_safely(self):
        """Manager should initialize storage directory and file without failing."""
        self.assertTrue(self.memory_file.exists())
        data = self.manager.load()
        self.assertEqual(data.get("user_profile"), {})
        self.assertEqual(data.get("communication_rules"), [])
        self.assertEqual(data.get("facts"), {})

    def test_corrupt_file_handling(self):
        """Corrupt JSON file must fall back gracefully to default structure without crash."""
        self.memory_file.write_text("{ corrupt json: [unclosed", encoding="utf-8")
        data = self.manager.load()
        self.assertEqual(data.get("user_profile"), {})
        self.assertEqual(data.get("communication_rules"), [])
        self.assertEqual(data.get("facts"), {})
        self.assertEqual(self.manager.build_system_context(), "")

    def test_set_and_delete_user_profile(self):
        """Setting and deleting user_profile attributes works correctly."""
        ok = self.manager.set_fact("user_profile", "name", "Fathan")
        self.assertTrue(ok)
        ok = self.manager.set_fact("user_profile", "role", "Senior Architect")
        self.assertTrue(ok)

        data = self.manager.load()
        self.assertEqual(data["user_profile"]["name"], "Fathan")
        self.assertEqual(data["user_profile"]["role"], "Senior Architect")

        # Delete key
        deleted = self.manager.delete_fact("user_profile", "role")
        self.assertTrue(deleted)
        data = self.manager.load()
        self.assertNotIn("role", data["user_profile"])
        self.assertEqual(data["user_profile"]["name"], "Fathan")

    def test_set_and_delete_communication_rules(self):
        """Adding and removing communication rules works correctly and avoids duplicates."""
        ok1 = self.manager.set_fact("communication_rules", "", "Prefer concise code examples.")
        self.assertTrue(ok1)
        # Duplicate rule should not be added twice
        ok2 = self.manager.set_fact("communication_rules", "", "Prefer concise code examples.")
        self.assertTrue(ok2)

        data = self.manager.load()
        self.assertEqual(len(data["communication_rules"]), 1)
        self.assertEqual(data["communication_rules"][0], "Prefer concise code examples.")

        # Delete rule
        del_ok = self.manager.delete_fact("communication_rules", "Prefer concise code examples.")
        self.assertTrue(del_ok)
        self.assertEqual(self.manager.load()["communication_rules"], [])

    def test_set_and_delete_facts(self):
        """Setting and deleting arbitrary user facts."""
        ok = self.manager.set_fact("facts", "favorite_editor", "Neovim")
        self.assertTrue(ok)
        self.assertEqual(self.manager.load()["facts"]["favorite_editor"], "Neovim")

        del_ok = self.manager.delete_fact("facts", "favorite_editor")
        self.assertTrue(del_ok)
        self.assertNotIn("favorite_editor", self.manager.load()["facts"])

    def test_build_system_context_formatting(self):
        """build_system_context format must adhere to exact specification."""
        # Empty memory -> returns empty string (token efficient)
        self.assertEqual(self.manager.build_system_context(), "")

        # Populated memory
        self.manager.set_fact("user_profile", "name", "Fathan")
        self.manager.set_fact("communication_rules", "", "Always provide type hints in Python.")
        self.manager.set_fact("facts", "timezone", "Asia/Jakarta")

        context = self.manager.build_system_context()
        self.assertIn("<global_user_memory>", context)
        self.assertIn("</global_user_memory>", context)
        self.assertIn("[User Profile]\n- name: Fathan", context)
        self.assertIn("[Rules]\n- Always provide type hints in Python.", context)
        self.assertIn("[Facts]\n- timezone: Asia/Jakarta", context)

    def test_memory_tool_execution(self):
        """Test update_user_memory tool invocation through tool registry."""
        tools = get_all_assistant_tools()
        tool_names = [t["function"]["name"] for t in tools]
        self.assertIn("update_user_memory", tool_names)

        # Execute tool via execute_tool
        res = execute_tool(
            "update_user_memory",
            {"action": "set", "category": "user_profile", "key": "preferred_language", "value": "Python"},
        )
        self.assertIn("Successfully", res)

        rule_res = execute_tool(
            "update_user_memory",
            {"action": "set", "category": "communication_rules", "value": "Be direct and concise."},
        )
        self.assertIn("Successfully", rule_res)

        del_res = execute_tool(
            "update_user_memory",
            {"action": "delete", "category": "user_profile", "key": "preferred_language"},
        )
        self.assertIn("Successfully removed", del_res)

    def test_memory_tool_security_policy(self):
        """Sensitive credentials like API keys or passwords must be blocked from memory."""
        res_key = execute_tool(
            "update_user_memory",
            {"action": "set", "category": "facts", "key": "api_key", "value": "sk-abcdef1234567890abcdef12"},
        )
        self.assertIn("Security policy prevents storing sensitive secrets", res_key)

        res_pwd = execute_tool(
            "update_user_memory",
            {"action": "set", "category": "facts", "key": "creds", "value": "password='supersecretpass123'"},
        )
        self.assertIn("Security policy prevents storing sensitive secrets", res_pwd)

    def test_memory_tool_cot_stripping(self):
        """Raw Chain-of-Thought tags must be stripped before persisting."""
        res = execute_tool(
            "update_user_memory",
            {
                "action": "set",
                "category": "facts",
                "key": "framework",
                "value": "<think>The user prefers FastAPI</think>FastAPI",
            },
        )
        self.assertIn("Successfully", res)
        # Verify stored value does not contain think tags
        mgr = GlobalMemoryManager()
        stored = mgr.load()["facts"].get("framework")
        self.assertEqual(stored, "FastAPI")

    def test_context_order_in_api_server(self):
        """Verify message assembly order: Base -> Global Memory -> Workspace Instructions -> History -> User."""
        from locallm.modules.api_server import OpenAIAPIHandler
        from locallm.config import LocaLLMConfig

        cfg = LocaLLMConfig(system_prompt="BASE_SYSTEM_INSTRUCTION")
        server_stub = type("DummyServer", (), {"config": cfg})()

        # Set up a known global memory
        mgr = GlobalMemoryManager()
        mgr.set_fact("user_profile", "test_user", "Tester")

        handler = OpenAIAPIHandler.__new__(OpenAIAPIHandler)
        handler.server = server_stub

        messages = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
            {"role": "user", "content": "Current question"},
        ]
        ws_context = "[Workspace Instructions]\nTest workspace directives"

        prepared = handler._prepare_messages_with_context(messages, ws_context)

        self.assertEqual(len(prepared), 4)
        sys_msg = prepared[0]
        self.assertEqual(sys_msg["role"], "system")
        sys_content = sys_msg["content"]

        # Check order
        idx_base = sys_content.find("BASE_SYSTEM_INSTRUCTION")
        idx_mem = sys_content.find("<global_user_memory>")
        idx_ws = sys_content.find("[Workspace Instructions]")

        self.assertNotEqual(idx_base, -1)
        self.assertNotEqual(idx_mem, -1)
        self.assertNotEqual(idx_ws, -1)

        self.assertLess(idx_base, idx_mem, "Base instructions must precede Global Memory")
        self.assertLess(idx_mem, idx_ws, "Global Memory must precede Workspace Instructions")

        # History remains intact after system prompt
        self.assertEqual(prepared[1]["content"], "Previous question")
        self.assertEqual(prepared[2]["content"], "Previous answer")
        self.assertEqual(prepared[3]["content"], "Current question")

        # Clean up test fact
        mgr.delete_fact("user_profile", "test_user")

    def test_cross_workspace_isolation_and_shared_memory(self):
        """Workspace sessions remain isolated while Global Memory is shared."""
        from locallm.core.workspace import (
            create_workspace,
            delete_workspace,
            save_workspace_session,
            load_workspace_session,
        )
        from locallm.core.memory import ConversationMemory

        ws_a = "test_workspace_alpha"
        ws_b = "test_workspace_beta"

        create_workspace(ws_a)
        create_workspace(ws_b)

        try:
            # Set global memory
            mgr = GlobalMemoryManager()
            mgr.set_fact("communication_rules", "", "Reply in Indonesian.")

            # Create session in Workspace A
            mem_a = ConversationMemory()
            mem_a.add_user_message("Secret data from Workspace A")
            mem_a.add_assistant_message("Acknowledged Workspace A")
            save_workspace_session(ws_a, "session_1", mem_a)

            # Create session in Workspace B
            mem_b = ConversationMemory()
            mem_b.add_user_message("Hello from Workspace B")
            mem_b.add_assistant_message("Acknowledged Workspace B")
            save_workspace_session(ws_b, "session_1", mem_b)

            # 1. Workspace isolation check: Workspace B session must NOT contain Workspace A history
            loaded_b = load_workspace_session(ws_b, "session_1")
            b_messages = [m["content"] for m in loaded_b.history]
            self.assertNotIn("Secret data from Workspace A", b_messages)
            self.assertIn("Hello from Workspace B", b_messages)

            # 2. Shared Global Memory check: Both workspaces see the shared preference
            sys_context = mgr.build_system_context()
            self.assertIn("Reply in Indonesian.", sys_context)

            # Clean up rule
            mgr.delete_fact("communication_rules", "Reply in Indonesian.")
        finally:
            delete_workspace(ws_a, "default")
            delete_workspace(ws_b, "default")


if __name__ == "__main__":
    unittest.main()
