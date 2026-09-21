"""Unit tests for built-in assistant tools."""

import unittest
from locallm.core.tools import ASSISTANT_TOOLS, execute_tool


class TestTools(unittest.TestCase):
    """Test built-in tool function definitions and executions."""

    def test_assistant_tools_schema(self):
        self.assertIsInstance(ASSISTANT_TOOLS, list)
        tool_names = [t["function"]["name"] for t in ASSISTANT_TOOLS]
        self.assertIn("get_current_time", tool_names)
        self.assertIn("get_current_directory", tool_names)
        self.assertIn("list_directory", tool_names)
        self.assertIn("read_file", tool_names)
        self.assertIn("write_file", tool_names)
        self.assertIn("create_directory", tool_names)

    def test_execute_write_file_and_create_directory(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmpdir:
            test_sub_dir = Path(tmpdir) / "test_nested" / "project"
            res_dir = execute_tool("create_directory", {"path": str(test_sub_dir)})
            self.assertIn("Successfully created directory", res_dir)
            self.assertTrue(test_sub_dir.exists())

            test_file = test_sub_dir / "app.py"
            test_content = "print('Hello from locaLLM!')\n"
            res_file = execute_tool("write_file", {"path": str(test_file), "content": test_content})
            self.assertIn("Successfully wrote", res_file)
            self.assertTrue(test_file.exists())
            self.assertEqual(test_file.read_text(encoding="utf-8"), test_content)

    def test_execute_get_current_time(self):
        result = execute_tool("get_current_time", {})
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 5)

    def test_execute_get_current_directory(self):
        result = execute_tool("get_current_directory", {})
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_execute_list_directory(self):
        result = execute_tool("list_directory", {"path": "."})
        self.assertIsInstance(result, str)
        self.assertIn("[FILE]", result)

    def test_execute_unknown_tool(self):
        result = execute_tool("non_existent_tool", {})
        self.assertIn("Unknown tool", result)

    def test_get_weather_schema(self):
        tool_names = [t["function"]["name"] for t in ASSISTANT_TOOLS]
        self.assertIn("get_weather", tool_names)
        # Empty location error check
        res = execute_tool("get_weather", {"location": ""})
        self.assertIn("Error", res)

    def test_permission_policy_deny(self):
        result = execute_tool(
            "write_file",
            {"path": "dummy.txt", "content": "hello"},
            permission_policy="deny",
        )
        self.assertIn("[Permission Denied]", result)

    def test_permission_policy_session_override(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "override.txt"
            result = execute_tool(
                "write_file",
                {"path": str(target), "content": "session allowed"},
                permission_policy="deny",
                session_state={"permission_override": "always_allow"},
            )
            self.assertIn("Successfully wrote", result)
            self.assertTrue(target.exists())

    def test_skills_tools_execution(self):
        tool_names = [t["function"]["name"] for t in ASSISTANT_TOOLS]
        self.assertIn("list_skills", tool_names)
        self.assertIn("read_skill", tool_names)

        list_res = execute_tool("list_skills", {})
        self.assertIsInstance(list_res, str)

        read_res = execute_tool("read_skill", {"skill_name": "non_existent_mock_skill_123"})
        self.assertIn("not found", read_res)


if __name__ == "__main__":
    unittest.main()
