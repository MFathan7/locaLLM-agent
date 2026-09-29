"""Unit tests for Model Context Protocol (MCP) multi-server architecture."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

from locallm.core.mcp.client import MCPClient
from locallm.core.mcp.manager import MCPManager
from locallm.core.mcp.models import MCPServerConfig, MCPToolInfo
from locallm.core.tools import execute_tool, get_all_assistant_tools, get_caller_tools


# Minimal Standalone Mock MCP Server Script
MOCK_MCP_SERVER_CODE = """
import sys
import json

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        method = req.get("method")
        req_id = req.get("id")

        if method == "initialize":
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": True}},
                    "serverInfo": {"name": "mock-mcp-server", "version": "1.0.0"}
                }
            }
            sys.stdout.write(json.dumps(res) + "\\n")
            sys.stdout.flush()

        elif method == "notifications/initialized":
            # One-way notification
            pass

        elif method == "tools/list":
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "multiply",
                            "description": "Multiply two numbers together",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "a": {"type": "number"},
                                    "b": {"type": "number"}
                                },
                                "required": ["a", "b"]
                            }
                        },
                        {
                            "name": "echo",
                            "description": "Echo back input text",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"}
                                }
                            }
                        }
                    ]
                }
            }
            sys.stdout.write(json.dumps(res) + "\\n")
            sys.stdout.flush()

        elif method == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})

            if name == "multiply":
                a = float(args.get("a", 0))
                b = float(args.get("b", 0))
                calc_val = a * b
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": str(calc_val)}],
                        "isError": False
                    }
                }
            elif name == "echo":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Echo: {args.get('text', '')}"}],
                        "isError": False
                    }
                }
            else:
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                        "isError": True
                    }
                }
            sys.stdout.write(json.dumps(res) + "\\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
"""


class TestMCPMultiServer(unittest.TestCase):
    """Test suite verifying Model Context Protocol (MCP) multi-connection support."""

    def test_mcp_server_config_serialization(self):
        """Verify MCPServerConfig serialization and deserialization."""
        cfg = MCPServerConfig(
            name="github",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "secret123"},
            enabled=True,
            privileged=True,
            description="GitHub MCP Tools",
        )
        data = cfg.to_dict()
        self.assertEqual(data["command"], "npx")
        self.assertEqual(data["privileged"], True)
        self.assertEqual(data["env"]["GITHUB_TOKEN"], "secret123")

        reconstructed = MCPServerConfig.from_dict("github", data)
        self.assertEqual(reconstructed.name, "github")
        self.assertEqual(reconstructed.transport, "stdio")
        self.assertEqual(reconstructed.privileged, True)
        self.assertEqual(reconstructed.args, ["-y", "@modelcontextprotocol/server-github"])

    def test_mcp_tool_info_to_openai_schema(self):
        """Verify MCPToolInfo produces valid OpenAI/Ollama function calling schema."""
        tool = MCPToolInfo(
            server_name="postgres",
            name="query",
            namespaced_name="mcp__postgres__query",
            description="Execute SQL query",
            input_schema={
                "type": "object",
                "properties": {"sql": {"type": "string"}},
                "required": ["sql"],
            },
            is_privileged=True,
        )
        schema = tool.to_openai_schema()
        self.assertEqual(schema["type"], "function")
        func = schema["function"]
        self.assertEqual(func["name"], "mcp__postgres__query")
        self.assertIn("[MCP: postgres]", func["description"])
        self.assertIn("sql", func["parameters"]["properties"])

    def test_multi_server_config_management(self):
        """Verify managing multiple concurrent MCP server configs simultaneously."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config_path = Path(tmpdir) / "mcp_servers.json"

            # Create manager and patch global config path
            manager = MCPManager()
            import locallm.core.mcp.manager as mgr_module

            orig_path_fn = mgr_module.get_global_mcp_config_path
            try:
                mgr_module.get_global_mcp_config_path = lambda: test_config_path

                # 1. Add server 1: Database
                db_cfg = MCPServerConfig(
                    name="database",
                    command="python",
                    args=["-m", "mcp_db"],
                    privileged=True,
                )
                manager.save_config(db_cfg)

                # 2. Add server 2: Search
                search_cfg = MCPServerConfig(
                    name="search",
                    command="npx",
                    args=["-y", "mcp-search"],
                    privileged=False,
                )
                manager.save_config(search_cfg)

                # 3. Add server 3: Cloud (SSE)
                cloud_cfg = MCPServerConfig(
                    name="cloud",
                    transport="sse",
                    url="http://127.0.0.1:9000/sse",
                    privileged=False,
                )
                manager.save_config(cloud_cfg)

                # Verify all 3 servers are loaded
                loaded = manager.load_configs()
                self.assertEqual(len(loaded), 3)
                self.assertIn("database", loaded)
                self.assertIn("search", loaded)
                self.assertIn("cloud", loaded)
                self.assertTrue(loaded["database"].privileged)
                self.assertEqual(loaded["cloud"].transport, "sse")

                # Remove server
                removed = manager.remove_config("search")
                self.assertTrue(removed)
                loaded_after = manager.load_configs()
                self.assertEqual(len(loaded_after), 2)
                self.assertNotIn("search", loaded_after)
            finally:
                mgr_module.get_global_mcp_config_path = orig_path_fn

    def test_mock_mcp_server_stdio_communication(self):
        """Verify real JSON-RPC handshake, tool listing, and tool execution with a live mock MCP server."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server_script = Path(tmpdir) / "mock_mcp_server.py"
            server_script.write_text(MOCK_MCP_SERVER_CODE, encoding="utf-8")

            cfg = MCPServerConfig(
                name="math_service",
                command=sys.executable,
                args=[str(server_script)],
                privileged=False,
            )

            client = MCPClient(cfg)
            try:
                # 1. Connect & Initialize
                client.connect_and_initialize(timeout=10.0)
                self.assertEqual(client.server_info.get("name"), "mock-mcp-server")

                # 2. Discover Tools
                tools = client.refresh_tools(timeout=5.0)
                self.assertEqual(len(tools), 2)
                tool_names = {t.name for t in tools}
                self.assertIn("multiply", tool_names)
                self.assertIn("echo", tool_names)

                # 3. Call Tool (multiply: 6 * 7 = 42)
                result = client.call_tool("multiply", {"a": 6, "b": 7}, timeout=5.0)
                self.assertEqual(result, "42.0")

                # 4. Call Tool (echo)
                echo_res = client.call_tool("echo", {"text": "locaLLM MCP rocks!"}, timeout=5.0)
                self.assertIn("locaLLM MCP rocks!", echo_res)
            finally:
                client.close()

    def test_mcp_tool_integration_and_access_control(self):
        """Verify MCP tools are seamlessly integrated with locaLLM central tool dispatch and role-based gating."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server_script = Path(tmpdir) / "mock_mcp_server.py"
            server_script.write_text(MOCK_MCP_SERVER_CODE, encoding="utf-8")

            # Privileged server: tools require admin privilege
            cfg = MCPServerConfig(
                name="calc_priv",
                command=sys.executable,
                args=[str(server_script)],
                privileged=True,
            )

            manager = MCPManager()
            test_config_path = Path(tmpdir) / "mcp_servers.json"

            import locallm.core.mcp.manager as mgr_module

            orig_path_fn = mgr_module.get_global_mcp_config_path
            try:
                mgr_module.get_global_mcp_config_path = lambda: test_config_path
                manager.save_config(cfg)

                # 1. Verify get_all_assistant_tools includes the MCP tool
                all_tools = get_all_assistant_tools()
                names = [t["function"]["name"] for t in all_tools]
                self.assertTrue(any("calc_priv" in n for n in names))

                # 2. Privileged tool gating
                # For unauthorized callers, the privileged MCP tools must be stripped
                unauth_tools = get_caller_tools(is_authorized=False)
                unauth_names = [t["function"]["name"] for t in unauth_tools]
                self.assertFalse(any("calc_priv" in n for n in unauth_names))

                # For authorized callers, the privileged MCP tools are included
                auth_tools = get_caller_tools(is_authorized=True)
                auth_names = [t["function"]["name"] for t in auth_tools]
                self.assertTrue(any("calc_priv" in n for n in auth_names))

                # 3. Execution authorization check
                mcp_func_name = "mcp__calc_priv__multiply"
                # Unauthorized caller blocked by runtime privilege check
                denied_res = execute_tool(
                    mcp_func_name,
                    {"a": 5, "b": 10},
                    session_state={"is_authorized": False},
                )
                self.assertEqual(denied_res, "Access denied. Administrative privileges required.")

                # Authorized caller executes successfully
                allowed_res = execute_tool(
                    mcp_func_name,
                    {"a": 5, "b": 10},
                    session_state={"is_authorized": True},
                )
                self.assertEqual(allowed_res, "50.0")
            finally:
                manager.close_all()
    def test_mcp_cli_add_command(self):
        """Verify streamlined CLI 'locallm mcp add' correctly infers and saves configurations."""
        from argparse import Namespace
        from locallm.cli import _handle_mcp_add
        import locallm.core.mcp.manager as mgr_module

        with tempfile.TemporaryDirectory() as tmpdir:
            test_config_path = Path(tmpdir) / "mcp_servers.json"
            orig_path_fn = mgr_module.get_global_mcp_config_path
            mgr_module.get_global_mcp_config_path = lambda: test_config_path

            try:
                # 1. Single executable command (e.g. locallm mcp add sample-cli-mcp)
                args1 = Namespace(name="sample-cli-mcp", command=[], url="", scope="global", privileged=False, desc="", env=[])
                _handle_mcp_add(args1, "default")
                cfg1 = mgr_module.mcp_manager.load_configs()["sample-cli-mcp"]
                self.assertEqual(cfg1.name, "sample-cli-mcp")
                self.assertEqual(cfg1.command, "sample-cli-mcp")
                self.assertEqual(cfg1.args, [])
                self.assertEqual(cfg1.transport, "stdio")

                # 2. Runner package syntax (e.g. locallm mcp add npx -y sample-cli-mcp)
                args2 = Namespace(name="npx", command=["-y", "sample-cli-mcp"], url="", scope="global", privileged=False, desc="", env=[])
                _handle_mcp_add(args2, "default")
                cfg2 = mgr_module.mcp_manager.load_configs()["sample-cli-mcp"]
                self.assertEqual(cfg2.name, "sample-cli-mcp")
                self.assertEqual(cfg2.command, "npx")
                self.assertEqual(cfg2.args, ["-y", "sample-cli-mcp"])

                # 3. Explicit server name with runner and env (e.g. locallm mcp add github npx -y @modelcontextprotocol/server-github -e GITHUB_TOKEN=xyz)
                args3 = Namespace(
                    name="github",
                    command=["npx", "-y", "@modelcontextprotocol/server-github"],
                    url="",
                    scope="global",
                    privileged=True,
                    desc="GitHub tools",
                    env=["GITHUB_TOKEN=xyz"],
                )
                _handle_mcp_add(args3, "default")
                cfg3 = mgr_module.mcp_manager.load_configs()["github"]
                self.assertEqual(cfg3.name, "github")
                self.assertEqual(cfg3.command, "npx")
                self.assertEqual(cfg3.args, ["-y", "@modelcontextprotocol/server-github"])
                self.assertEqual(cfg3.env, {"GITHUB_TOKEN": "xyz"})
                self.assertTrue(cfg3.privileged)

                # 4. SSE / Remote URL (e.g. locallm mcp add weather_svc http://127.0.0.1:8000/sse)
                args4 = Namespace(name="weather_svc", command=["http://127.0.0.1:8000/sse"], url="", scope="global", privileged=False, desc="", env=[])
                _handle_mcp_add(args4, "default")
                cfg4 = mgr_module.mcp_manager.load_configs()["weather_svc"]
                self.assertEqual(cfg4.name, "weather_svc")
                self.assertEqual(cfg4.transport, "sse")
                self.assertEqual(cfg4.url, "http://127.0.0.1:8000/sse")
            finally:
                mgr_module.mcp_manager.close_all()
                mgr_module.get_global_mcp_config_path = orig_path_fn


if __name__ == "__main__":
    unittest.main()
