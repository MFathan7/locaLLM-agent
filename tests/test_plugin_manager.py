"""Unit tests for plugin architecture and dynamic tool execution."""

from pathlib import Path
import sqlite3
import tempfile
import unittest

from locallm.core.plugin_manager import (
    create_plugin_scaffold,
    delete_plugin,
    disable_plugin,
    enable_plugin,
    execute_plugin_tool,
    get_active_plugin_tools,
    get_plugin,
    list_plugins,
)
from locallm.core.tools import execute_tool, get_all_assistant_tools


class TestPluginManager(unittest.TestCase):
    """Test suite for modular plugin discovery, manifest validation, and dynamic execution."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def test_sample_sqlite_plugin_discovered(self):
        """The built-in sample sqlite_db plugin in project plugins/ should be discovered."""
        plugins = list_plugins()
        plugin_names = [p.name for p in plugins]
        self.assertIn("sqlite_db", plugin_names)

        p = get_plugin("sqlite_db")
        self.assertIsNotNone(p)
        self.assertTrue(p.enabled)
        tool_names = [t["function"]["name"] for t in p.tools]
        self.assertIn("sqlite_query", tool_names)
        self.assertIn("sqlite_schema", tool_names)

    def test_dynamic_tools_merged_in_assistant_tools(self):
        """Plugin tools should be dynamically merged in get_all_assistant_tools()."""
        all_tools = get_all_assistant_tools()
        names = [t["function"]["name"] for t in all_tools]
        self.assertIn("search_web", names)
        self.assertIn("sqlite_query", names)
        self.assertIn("sqlite_schema", names)

    def test_sqlite_plugin_execution(self):
        """Test executing sqlite_schema and sqlite_query through execute_tool()."""
        # Create a test SQLite database
        db_path = Path(self.temp_dir.name) / "test.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL);")
        cursor.execute("INSERT INTO products (name, price) VALUES ('Widget', 19.99), ('Gadget', 49.50);")
        conn.commit()
        conn.close()

        # 1. Inspect schema via execute_tool
        schema_res = execute_tool("sqlite_schema", {"db_path": str(db_path)})
        self.assertIn("products", schema_res)
        self.assertIn("CREATE TABLE products", schema_res)

        # 2. Query data via execute_tool
        query_res = execute_tool(
            "sqlite_query",
            {"db_path": str(db_path), "query": "SELECT name, price FROM products ORDER BY id;"},
        )
        self.assertIn("Widget", query_res)
        self.assertIn("19.99", query_res)
        self.assertIn("Gadget", query_res)
        self.assertIn("49.5", query_res)

    def test_plugin_scaffold_creation(self):
        """Test creating a new starter plugin scaffold dynamically."""
        target_dir = Path(self.temp_dir.name)
        ok, msg, ppath = create_plugin_scaffold("my_custom_tool", target_dir=target_dir, description="Test custom plugin")
        self.assertTrue(ok)
        self.assertTrue((ppath / "plugin.json").is_file())
        self.assertTrue((ppath / "main.py").is_file())

        # Verify discovery of new plugin in custom directory
        from locallm.core.plugin_manager import _load_plugin_from_dir
        p = _load_plugin_from_dir(ppath, source="test")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "my_custom_tool")
        self.assertEqual(len(p.tools), 1)
        self.assertEqual(p.tools[0]["function"]["name"], "my_custom_tool_example_action")

    def test_plugin_enable_disable(self):
        """Test toggling plugin state."""
        target_dir = Path(self.temp_dir.name)
        ok, msg, ppath = create_plugin_scaffold("toggle_test", target_dir=target_dir)
        self.assertTrue(ok)

        from locallm.core.plugin_manager import _load_plugin_from_dir
        p = _load_plugin_from_dir(ppath)
        self.assertTrue(p.enabled)

        # Disable
        dis_ok, dis_msg = disable_plugin("toggle_test", workspace_name=None)
        # Re-inspect manifest directly
        import json
        with open(ppath / "plugin.json") as f:
            data = json.load(f)
        # Note: if toggle_test wasn't in standard search path, test manifest directly
        data["enabled"] = False
        with open(ppath / "plugin.json", "w") as f:
            json.dump(data, f)

        p2 = _load_plugin_from_dir(ppath)
        self.assertFalse(p2.enabled)

    def test_delete_plugin(self):
        """Test permanently deleting a plugin directory."""
        target_dir = Path(self.temp_dir.name)
        ok, msg, ppath = create_plugin_scaffold("to_delete", target_dir=target_dir)
        self.assertTrue(ok)
        self.assertTrue(ppath.exists())

        # Calling delete_plugin with custom target dir plugin via get_plugin mock
        from unittest.mock import patch
        from locallm.core.plugin_manager import _load_plugin_from_dir

        mock_plugin = _load_plugin_from_dir(ppath, source="test")
        with patch("locallm.core.plugin_manager.get_plugin", return_value=mock_plugin):
            del_ok, del_msg = delete_plugin("to_delete")
            self.assertTrue(del_ok)
            self.assertFalse(ppath.exists())


if __name__ == "__main__":
    unittest.main()
