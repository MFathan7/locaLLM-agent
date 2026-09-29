"""Unit tests for the modular tool registry, boundary protection, and dynamic pagination."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from locallm.core.tools import (
    ASSISTANT_TOOLS,
    TELEGRAM_TOOLS,
    WHATSAPP_TOOLS,
    BaseTool,
    ToolRegistry,
    execute_tool,
    registry,
    resolve_smart_path,
    tool,
)
from locallm.core.tools.filesystem import read_file_fn
from locallm.core.tools.web import fetch_web_fn


class TestModularTools(unittest.TestCase):
    """Test suite for modular tool registry, pagination, and boundary protection."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = Path(self.temp_dir.name).resolve()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_tool_registry_registration_and_schemas(self) -> None:
        """Test ToolRegistry registers tools and filters schemas by category."""
        custom_reg = ToolRegistry()

        @tool(
            name="dummy_tool",
            description="A dummy test tool",
            parameters={"type": "object", "properties": {"msg": {"type": "string"}}},
            is_mutating=True,
            categories={"assistant", "custom"},
            reg=custom_reg,
        )
        def dummy_action(msg: str = "hello") -> str:
            return f"Dummy: {msg}"

        tool_obj = custom_reg.get("dummy_tool")
        self.assertIsNotNone(tool_obj)
        self.assertTrue(tool_obj.is_mutating)
        self.assertEqual(tool_obj.execute({"msg": "world"}), "Dummy: world")

        # Schemas
        assistant_schemas = custom_reg.get_schemas("assistant")
        self.assertEqual(len(assistant_schemas), 1)
        self.assertEqual(assistant_schemas[0]["function"]["name"], "dummy_tool")

        # Category filter excludes unmatching
        other_schemas = custom_reg.get_schemas("other")
        self.assertEqual(len(other_schemas), 0)

        # Mutating tools set
        self.assertIn("dummy_tool", custom_reg.get_mutating_tool_names())

    def test_schema_includes_pagination_parameters(self) -> None:
        """Verify read_file and fetch_web schemas define offset and max_chars."""
        read_file_schema = next(
            t["function"] for t in ASSISTANT_TOOLS if t["function"]["name"] == "read_file"
        )
        self.assertIn("offset", read_file_schema["parameters"]["properties"])
        self.assertIn("max_chars", read_file_schema["parameters"]["properties"])

        fetch_web_schema = next(
            t["function"] for t in ASSISTANT_TOOLS if t["function"]["name"] == "fetch_web"
        )
        self.assertIn("offset", fetch_web_schema["parameters"]["properties"])
        self.assertIn("max_chars", fetch_web_schema["parameters"]["properties"])

    def test_boundary_path_traversal_protection(self) -> None:
        """Verify resolve_smart_path enforces boundary_dir restriction."""
        sandbox = self.root_path / "sandbox"
        sandbox.mkdir(parents=True, exist_ok=True)
        safe_file = sandbox / "allowed.txt"
        safe_file.write_text("safe content", encoding="utf-8")

        # Safe access inside boundary
        resolved = resolve_smart_path(str(safe_file), boundary_dir=sandbox)
        self.assertEqual(resolved, safe_file)

        # Traversal attempt outside boundary
        outside_file = self.root_path / "secret.txt"
        outside_file.write_text("secret", encoding="utf-8")

        with self.assertRaises(PermissionError):
            resolve_smart_path(str(outside_file), boundary_dir=sandbox)

        # Relative traversal
        with self.assertRaises(PermissionError):
            resolve_smart_path("../secret.txt", boundary_dir=sandbox)

    def test_read_file_pagination_and_chunking(self) -> None:
        """Verify read_file returns paginated chunks with guidance on next offset."""
        test_file = self.root_path / "sample.txt"
        content = "0123456789" * 10  # 100 characters
        test_file.write_text(content, encoding="utf-8")

        # Chunk 1: first 30 chars
        res_chunk1 = read_file_fn(str(test_file), offset=0, max_chars=30)
        self.assertIn("[Showing characters 0 to 30 of 100", res_chunk1)
        self.assertIn("offset=30", res_chunk1)
        self.assertTrue(res_chunk1.endswith("012345678901234567890123456789"))

        # Chunk 2: offset 30, length 30
        res_chunk2 = read_file_fn(str(test_file), offset=30, max_chars=30)
        self.assertIn("[Showing characters 30 to 60 of 100", res_chunk2)
        self.assertIn("offset=60", res_chunk2)

        # Chunk 3: offset 60, length 50 (reads to end of file)
        res_chunk3 = read_file_fn(str(test_file), offset=60, max_chars=50)
        self.assertIn("(End of file)", res_chunk3)

        # Offset beyond length
        res_beyond = read_file_fn(str(test_file), offset=150, max_chars=30)
        self.assertIn("Error: Offset 150 is beyond the total file length", res_beyond)

    def test_fetch_web_pagination(self) -> None:
        """Verify fetch_web pagination when response text exceeds max_chars."""
        mock_html = "<html><body>" + ("<p>Text paragraph data</p>" * 50) + "</body></html>"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = mock_html
        mock_resp.headers = {"content-type": "text/html"}

        with patch("httpx.Client.get", return_value=mock_resp):
            res_chunk1 = fetch_web_fn("https://example.com/long-article", offset=0, max_chars=100)
            self.assertIn("[Showing characters 0 to 100", res_chunk1)
            self.assertIn("offset=100", res_chunk1)

            res_chunk2 = fetch_web_fn("https://example.com/long-article", offset=100, max_chars=100)
            self.assertIn("[Showing characters 100 to 200", res_chunk2)

    def test_execute_tool_with_session_boundary(self) -> None:
        """Verify execute_tool respects session boundary context."""
        sandbox = self.root_path / "jail"
        sandbox.mkdir(parents=True, exist_ok=True)
        inside_file = sandbox / "doc.txt"
        inside_file.write_text("Jail document content", encoding="utf-8")

        outside_file = self.root_path / "escaped.txt"
        outside_file.write_text("Outside forbidden data", encoding="utf-8")

        session_state = {"boundary_dir": sandbox}

        # Reading file inside boundary succeeds
        obs = execute_tool(
            "read_file",
            {"path": str(inside_file)},
            session_state=session_state,
        )
        self.assertIn("Jail document content", obs)

        # Reading file outside boundary is blocked
        obs_blocked = execute_tool(
            "read_file",
            {"path": str(outside_file)},
            session_state=session_state,
        )
        self.assertIn("Access denied", obs_blocked)
        self.assertIn("escapes allowed boundary", obs_blocked)

    def test_resolve_path_existing_file(self) -> None:
        """Verify resolve_path returns accurate existence, type, and absolute path."""
        target_file = self.root_path / "test_doc.md"
        target_file.write_text("Markdown content for testing", encoding="utf-8")

        obs = execute_tool("resolve_path", {"path": str(target_file)})
        self.assertIn("Exists: True", obs)
        self.assertIn("Type: File", obs)
        self.assertIn("Absolute Path:", obs)
        self.assertIn("test_doc.md", obs)

    def test_resolve_path_nonexistent_and_search(self) -> None:
        """Verify resolve_path returns Exists: False when path not found."""
        nonexistent = self.root_path / "nowhere" / "missing.txt"
        obs = execute_tool("resolve_path", {"path": str(nonexistent)})
        self.assertIn("Exists: False", obs)

    def test_router_read_only_path_inspection_not_dispatched_to_coder(self) -> None:
        """Verify router does not classify read-only file/path inspection as a coding specialist task."""
        from locallm.config import LocaLLMConfig
        from locallm.core.router import TaskType, route_prompt

        config = LocaLLMConfig()
        config.default_model = "auto"

        mock_client = MagicMock()
        mock_client.list_models.return_value = [
            {"name": "gemma4:12b", "size": 12 * 1024**3},
            {"name": "qwen2.5-coder:14b", "size": 14 * 1024**3},
        ]
        mock_client.get_loaded_models.return_value = ["gemma4:12b"]
        mock_client.get_model_features.side_effect = lambda m: (
            ["Tools"] if "gemma" in m else ["Tools"]
        )

        prompt = "coba cari nama file ini, dan berikan full path filenya: ./reports/uv_latest.md"
        res = route_prompt(prompt, config, mock_client)

        # Should NOT dispatch to coder model for pure path lookup
        self.assertNotIn("qwen2.5-coder", res.selected_model)
        self.assertEqual(res.selected_model, "gemma4:12b")


if __name__ == "__main__":
    unittest.main()
