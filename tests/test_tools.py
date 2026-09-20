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

    def test_conversation_memory_images(self):
        from locallm.core.memory import ConversationMemory
        mem = ConversationMemory(system_prompt="Test sys")
        mem.add_user_message("Describe this", images=["base64mockdata"])
        msgs = mem.get_messages()
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[1]["role"], "user")
        self.assertEqual(msgs[1]["images"], ["base64mockdata"])


if __name__ == "__main__":
    unittest.main()
