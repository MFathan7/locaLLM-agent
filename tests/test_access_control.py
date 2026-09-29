"""Unit tests for role-based access control, tool gating, and security policy directives."""

import unittest
import tempfile
from pathlib import Path
import json

from locallm.config import LocaLLMConfig
from locallm.core.tools import (
    ASSISTANT_TOOLS,
    TELEGRAM_TOOLS,
    WHATSAPP_TOOLS,
    execute_tool,
    get_all_privileged_tools,
    get_caller_tools,
)
from locallm.core.workspace import (
    WorkspaceSecurityPolicy,
    get_workspace_security_policy,
)
from locallm.modules.telegram_bot import _check_telegram_caller_authorization


class TestAccessControlAndToolGating(unittest.TestCase):
    """Test suite verifying access control, markdown directive parsing, and tool gating."""

    def test_privileged_tools_identification(self):
        """Verify that filesystem and system execution tools are correctly tagged as privileged."""
        privileged = get_all_privileged_tools()
        self.assertIn("read_file", privileged)
        self.assertIn("write_file", privileged)
        self.assertIn("create_directory", privileged)
        self.assertIn("list_directory", privileged)
        self.assertIn("execute_command", privileged)
        self.assertIn("get_current_directory", privileged)

        # Non-privileged safe tools
        self.assertNotIn("get_current_time", privileged)
        self.assertNotIn("get_weather", privileged)

    def test_get_caller_tools_authorized(self):
        """Authorized callers must receive both privileged and unprivileged tools."""
        tools = get_caller_tools(is_authorized=True, category="assistant")
        names = {t["function"]["name"] for t in tools}
        self.assertIn("read_file", names)
        self.assertIn("write_file", names)
        self.assertIn("get_current_time", names)
        self.assertIn("execute_command", names)

    def test_get_caller_tools_unauthorized_filters_privileged(self):
        """Unauthorized callers must not see any privileged tools in their schema."""
        tools = get_caller_tools(is_authorized=False, category="assistant")
        names = {t["function"]["name"] for t in tools}
        self.assertNotIn("read_file", names)
        self.assertNotIn("write_file", names)
        self.assertNotIn("execute_command", names)
        self.assertNotIn("list_directory", names)
        self.assertIn("get_current_time", names)
        self.assertIn("get_weather", names)

    def test_get_caller_tools_custom_allow_override(self):
        """Custom public tools whitelist must take precedence for unauthorized callers."""
        allowed = {"get_current_time", "get_weather"}
        tools = get_caller_tools(
            is_authorized=False,
            category="assistant",
            allowed_tools_override=allowed,
        )
        names = {t["function"]["name"] for t in tools}
        self.assertEqual(names, allowed)

    def test_get_caller_tools_custom_deny_override(self):
        """Custom public tools deny list must remove specified tools."""
        denied = {"get_weather"}
        tools = get_caller_tools(
            is_authorized=False,
            category="assistant",
            denied_tools_override=denied,
        )
        names = {t["function"]["name"] for t in tools}
        self.assertNotIn("get_weather", names)
        self.assertIn("get_current_time", names)

    def test_execute_tool_privilege_enforcement(self):
        """Executing privileged tools must fail with Access Denied for unauthorized callers."""
        # Unprivileged tool succeeds
        time_res = execute_tool(
            "get_current_time",
            {},
            session_state={"is_authorized": False},
        )
        self.assertNotIn("Access denied", time_res)

        # Privileged tools are strictly blocked at runtime
        read_res = execute_tool(
            "read_file",
            {"path": "README.md"},
            session_state={"is_authorized": False},
        )
        self.assertEqual(read_res, "Access denied. Administrative privileges required.")

        cmd_res = execute_tool(
            "execute_command",
            {"command": "dir"},
            session_state={"is_authorized": False},
        )
        self.assertEqual(cmd_res, "Access denied. Administrative privileges required.")

        list_res = execute_tool(
            "list_directory",
            {"path": "."},
            session_state={"is_authorized": False},
        )
        self.assertEqual(list_res, "Access denied. Administrative privileges required.")

    def test_execute_tool_authorized_callers_allowed(self):
        """Executing privileged tools succeeds when is_authorized=True or unspecified."""
        # When authorized explicitly
        list_res = execute_tool(
            "list_directory",
            {"path": "."},
            session_state={"is_authorized": True},
        )
        self.assertNotEqual(list_res, "Access denied. Administrative privileges required.")

    def test_security_policy_directive_parsing(self):
        """Verify parsing of markdown security directives."""
        policy = get_workspace_security_policy("default")
        self.assertIsInstance(policy, WorkspaceSecurityPolicy)

    def test_telegram_caller_authorization_check(self):
        """Verify caller authorization check merges config and policy."""
        config = LocaLLMConfig()
        config.telegram_allowed_users = [11111111]

        # 1. Configured user is authorized
        is_auth, allowed = _check_telegram_caller_authorization(11111111, "default", config)
        self.assertTrue(is_auth)
        self.assertTrue(allowed)

        # 2. Random unwhitelisted user
        is_auth_rand, allowed_rand = _check_telegram_caller_authorization(99999999, "default", config)
        self.assertFalse(is_auth_rand)

    def test_owner_telegram_synonyms_and_username_parsing(self):
        """Verify that variations like OWNER TELEGRAM, ADMIN TELEGRAM, and usernames are parsed."""
        from locallm.core.workspace import get_workspace_path
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_md = (
                "# Agent Instructions\n"
                "* OWNER TELEGRAM: 655038084\n"
                "* TELEGRAM ADMIN: @superadmin\n"
                "* ADMIN_WHATSAPP: '628999888777'\n"
                "* [PUBLIC_TOOLS_ALLOW]\n"
                "- search_web\n"
                "- get_weather\n"
            )
            # Create a mock workspace
            ws_path = Path(tmpdir)
            (ws_path / "knowledge").mkdir(parents=True, exist_ok=True)
            (ws_path / "AGENTS.md").write_text(sample_md, encoding="utf-8")

            # Monkeypatch get_workspace_path for this test
            import locallm.core.workspace as ws_module
            orig_get_ws = ws_module.get_workspace_path
            try:
                ws_module.get_workspace_path = lambda name: ws_path
                policy = get_workspace_security_policy("mock_ws")
                self.assertIn(655038084, policy.master_telegram_ids)
                self.assertIn("superadmin", policy.master_telegram_usernames)
                self.assertIn("628999888777", policy.master_whatsapp_identifiers)
                self.assertIn("search_web", policy.public_allowed_tools)
                self.assertIn("get_weather", policy.public_allowed_tools)
            finally:
                ws_module.get_workspace_path = orig_get_ws

    def test_telegram_caller_authorization_by_username(self):
        """Verify that caller authorization succeeds if caller's username matches policy."""
        config = LocaLLMConfig()
        config.telegram_allowed_users = []

        import locallm.modules.telegram_bot as tb_module
        orig_get_policy = tb_module.get_workspace_security_policy
        try:
            mock_policy = WorkspaceSecurityPolicy()
            mock_policy.master_telegram_usernames.add("mfathan7")
            tb_module.get_workspace_security_policy = lambda name: mock_policy

            # Calling with matching username
            is_auth, allowed = _check_telegram_caller_authorization(
                99999999, "default", config, username="mfathan7"
            )
            self.assertTrue(is_auth)
            self.assertTrue(allowed)

            # Calling with matching username with @ prefix
            is_auth_at, allowed_at = _check_telegram_caller_authorization(
                99999999, "default", config, username="@mfathan7"
            )
            self.assertTrue(is_auth_at)
            self.assertTrue(allowed_at)

            # Calling with non-matching username
            is_auth_other, allowed_other = _check_telegram_caller_authorization(
                99999999, "default", config, username="random_user"
            )
            self.assertFalse(is_auth_other)
        finally:
            tb_module.get_workspace_security_policy = orig_get_policy


if __name__ == "__main__":
    unittest.main()
