"""Unit tests for workspace session persistence and Telegram/Chat markdown formatting."""

import shutil
import tempfile
import unittest
import json
from pathlib import Path
from locallm.core.memory import ConversationMemory
from locallm.core.tools import TELEGRAM_TOOLS
from locallm.core.workspace import (
    clear_all_workspace_sessions,
    delete_workspace_session,
    get_workspace_path,
    list_workspace_sessions,
    load_workspace_session,
    save_workspace_session,
)
from locallm.modules.telegram_bot import (
    BOT_COMMANDS,
    _execute_telegram_tool,
    markdown_to_telegram_html,
    split_telegram_message,
)


class TestSessionsAndFormatting(unittest.TestCase):
    """Test suite verifying session lifecycle and Telegram HTML parsing."""

    def setUp(self) -> None:
        self.test_ws = f"test_ws_{unittest.TestCase.id(self).split('.')[-1]}"
        self.ws_dir = get_workspace_path(self.test_ws)
        self.ws_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.ws_dir.exists():
            shutil.rmtree(self.ws_dir, ignore_errors=True)

    def test_memory_serialization_and_json(self) -> None:
        """Verify ConversationMemory dictionary export and JSON file persistence."""
        mem = ConversationMemory(system_prompt="System instructions")
        mem.add_user_message("Hello AI", images=["base64mockimage"])
        mem.add_assistant_message("Hello User, I can assist you.")

        data = mem.to_dict(metadata={"model": "test_model"})
        self.assertEqual(data["system_prompt"], "System instructions")
        self.assertEqual(len(data["history"]), 2)
        self.assertEqual(data["metadata"]["model"], "test_model")

        restored = ConversationMemory.from_dict(data)
        self.assertEqual(restored.system_prompt, "System instructions")
        self.assertEqual(len(restored.history), 2)
        self.assertEqual(restored.history[0]["content"], "Hello AI")
        self.assertEqual(restored.history[0]["images"], ["base64mockimage"])

        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "test_session.json"
            mem.save_to_json(json_file, metadata={"session_id": "test_123"})
            self.assertTrue(json_file.is_file())

            loaded_mem = ConversationMemory()
            loaded_mem.load_from_json(json_file)
            self.assertEqual(loaded_mem.system_prompt, "System instructions")
            self.assertEqual(len(loaded_mem.history), 2)

    def test_workspace_session_crud(self) -> None:
        """Verify save, list, load, and delete operations on workspace sessions."""
        mem = ConversationMemory(system_prompt="Active context")
        mem.add_user_message("Check system status")
        mem.add_assistant_message("All systems operational.")

        saved_path = save_workspace_session(
            self.test_ws,
            "session_alpha",
            mem,
            metadata={"type": "assistant", "model": "gemma4:12b"},
        )
        self.assertTrue(saved_path.is_file())
        self.assertEqual(saved_path.name, "session_alpha.json")

        sessions = list_workspace_sessions(self.test_ws)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["session_id"], "session_alpha")
        self.assertEqual(sessions[0]["type"], "assistant")
        self.assertEqual(sessions[0]["model"], "gemma4:12b")
        self.assertEqual(sessions[0]["message_count"], 2)
        self.assertIn("All systems operational", sessions[0]["last_snippet"])

        loaded = load_workspace_session(self.test_ws, "session_alpha")
        self.assertIsNotNone(loaded)
        if loaded:
            self.assertEqual(len(loaded.history), 2)
            self.assertEqual(loaded.history[1]["content"], "All systems operational.")

        deleted = delete_workspace_session(self.test_ws, "session_alpha")
        self.assertTrue(deleted)
        self.assertFalse(saved_path.exists())
        self.assertEqual(len(list_workspace_sessions(self.test_ws)), 0)

    def test_session_deletion_cascade_cleans_memory(self) -> None:
        """Verify that deleting a session automatically purges any extracted facts tied to that session."""
        from locallm.core.workspace_memory import WorkspaceMemoryManager
        ws_mem = WorkspaceMemoryManager(self.test_ws)
        ws_mem.set_fact("beli_ayam", "Membeli ayam kalkun", session_id="session_alpha")
        ws_mem.set_fact("project_goal", "Sistem AI lokal", session_id="session_beta")

        # Confirm both facts are present
        facts = ws_mem.list_facts()
        self.assertEqual(facts.get("beli_ayam"), "Membeli ayam kalkun")
        self.assertEqual(facts.get("project_goal"), "Sistem AI lokal")

        # Delete session_alpha
        delete_workspace_session(self.test_ws, "session_alpha")

        # Confirm session_alpha fact is purged, while session_beta fact remains
        updated_facts = ws_mem.list_facts()
        self.assertNotIn("beli_ayam", updated_facts)
        self.assertEqual(updated_facts.get("project_goal"), "Sistem AI lokal")

    def test_clear_all_workspace_sessions(self) -> None:
        """Verify mass deletion of session files in a workspace."""
        mem = ConversationMemory()
        mem.add_user_message("Test 1")
        save_workspace_session(self.test_ws, "sess_1", mem)
        save_workspace_session(self.test_ws, "sess_2", mem)
        save_workspace_session(self.test_ws, "sess_3", mem)

        self.assertEqual(len(list_workspace_sessions(self.test_ws)), 3)
        deleted_count = clear_all_workspace_sessions(self.test_ws)
        self.assertEqual(deleted_count, 3)
        self.assertEqual(len(list_workspace_sessions(self.test_ws)), 0)

    def test_session_type_filtering_and_selective_clear(self) -> None:
        """Verify session_type filtering isolates native chat sessions from Telegram, WhatsApp, and API sessions."""
        mem = ConversationMemory()
        mem.add_user_message("Test message")

        # Save various session types
        save_workspace_session(self.test_ws, "chat_20260929_100000", mem, metadata={"type": "assistant", "model": "gemma4:12b"})
        save_workspace_session(self.test_ws, "session_custom", mem, metadata={"type": "chat", "model": "qwen2.5-coder"})
        save_workspace_session(self.test_ws, "sess_plain", mem)
        save_workspace_session(self.test_ws, "telegram_12345678", mem, metadata={"type": "telegram", "user_id": 12345678})
        save_workspace_session(self.test_ws, "telegram_99999999", mem)
        save_workspace_session(self.test_ws, "whatsapp_628111111", mem, metadata={"type": "whatsapp", "phone_number": "628111111"})
        save_workspace_session(self.test_ws, "whatsapp_628222222", mem)
        save_workspace_session(self.test_ws, "api_request_abc", mem, metadata={"type": "api"})

        # Total sessions: 8
        all_sessions = list_workspace_sessions(self.test_ws)
        self.assertEqual(len(all_sessions), 8)

        # Chat / Assistant sessions: must strictly be the 3 chat sessions, never external channels
        chat_sessions = list_workspace_sessions(self.test_ws, session_type="assistant")
        chat_ids = {s["session_id"] for s in chat_sessions}
        self.assertEqual(len(chat_sessions), 3)
        self.assertEqual(chat_ids, {"chat_20260929_100000", "session_custom", "sess_plain"})
        self.assertNotIn("telegram_12345678", chat_ids)
        self.assertNotIn("telegram_99999999", chat_ids)
        self.assertNotIn("whatsapp_628111111", chat_ids)
        self.assertNotIn("whatsapp_628222222", chat_ids)
        self.assertNotIn("api_request_abc", chat_ids)

        # Telegram filtering
        tg_sessions = list_workspace_sessions(self.test_ws, session_type="telegram")
        tg_ids = {s["session_id"] for s in tg_sessions}
        self.assertEqual(len(tg_sessions), 2)
        self.assertEqual(tg_ids, {"telegram_12345678", "telegram_99999999"})

        # WhatsApp filtering
        wa_sessions = list_workspace_sessions(self.test_ws, session_type="whatsapp")
        wa_ids = {s["session_id"] for s in wa_sessions}
        self.assertEqual(len(wa_sessions), 2)
        self.assertEqual(wa_ids, {"whatsapp_628111111", "whatsapp_628222222"})

        # Selective clear of chat sessions: only deletes chat sessions, preserves Telegram & WhatsApp
        deleted_chat_count = clear_all_workspace_sessions(self.test_ws, session_type="assistant")
        self.assertEqual(deleted_chat_count, 3)

        self.assertEqual(len(list_workspace_sessions(self.test_ws, session_type="assistant")), 0)
        self.assertEqual(len(list_workspace_sessions(self.test_ws, session_type="telegram")), 2)
        self.assertEqual(len(list_workspace_sessions(self.test_ws, session_type="whatsapp")), 2)
        self.assertEqual(len(list_workspace_sessions(self.test_ws, session_type="api")), 1)

        # Full clear deletes remaining 5 external sessions
        deleted_remaining = clear_all_workspace_sessions(self.test_ws)
        self.assertEqual(deleted_remaining, 5)
        self.assertEqual(len(list_workspace_sessions(self.test_ws)), 0)

    def test_markdown_to_telegram_html(self) -> None:
        """Verify Markdown to Telegram HTML conversion for bold, code, links, and escaping."""
        raw_text = (
            "## Weather Report\n"
            "Hello **Antigravity**! Weather condition *today* is clear.\n"
            "Check `api_key` and run script:\n"
            "```python\n"
            "if temp < 30 and humid > 50:\n"
            "    print('Normal & Healthy')\n"
            "```\n"
            "Open [Website](https://weather.com) for details."
        )

        html_out = markdown_to_telegram_html(raw_text)

        # Bold conversion
        self.assertIn("<b>Weather Report</b>", html_out)
        self.assertIn("<b>Antigravity</b>", html_out)
        self.assertNotIn("**Antigravity**", html_out)

        # Italic conversion
        self.assertIn("<i>today</i>", html_out)

        # Inline code
        self.assertIn("<code>api_key</code>", html_out)

        # Code block with escaping of < and &
        self.assertIn('<pre><code class="language-python">', html_out)
        self.assertIn("&lt; 30 and humid &gt; 50", html_out)
        self.assertIn("Normal &amp; Healthy", html_out)

        # Link conversion
        self.assertIn('<a href="https://weather.com">Website</a>', html_out)

    def test_split_telegram_message(self) -> None:
        """Verify long message splitting respects character limits."""
        short_text = "Short telegram message"
        self.assertEqual(split_telegram_message(short_text, max_length=100), [short_text])

        para1 = "A" * 60
        para2 = "B" * 60
        long_text = f"{para1}\n\n{para2}"
        chunks = split_telegram_message(long_text, max_length=70)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], para1)
        self.assertEqual(chunks[1], para2)

    def test_telegram_tools_schema_and_execution(self) -> None:
        """Verify TELEGRAM_TOOLS registration and tool execution handling."""
        tool_names = [t["function"]["name"] for t in TELEGRAM_TOOLS]
        self.assertIn("telegram_get_user_info", tool_names)
        self.assertIn("telegram_send_photo", tool_names)
        self.assertIn("telegram_send_document", tool_names)
        self.assertIn("telegram_send_dice", tool_names)
        self.assertIn("telegram_send_sticker", tool_names)

        # Test execution with mock update
        class MockUser:
            id = 998877
            first_name = "Alex"
            last_name = "Smith"
            username = "alexsmith"
            full_name = "Alex Smith"
            language_code = "id"
            is_premium = False

        class MockChat:
            id = 998877
            type = "private"
            title = ""

        class MockMessage:
            async def reply_dice(self, emoji="🎲"):
                return True

            async def reply_photo(self, photo, caption=None, parse_mode=None):
                return True

            async def reply_document(self, document, caption=None, parse_mode=None):
                return True

            async def reply_sticker(self, sticker):
                return True

        class MockUpdate:
            effective_user = MockUser()
            effective_chat = MockChat()
            message = MockMessage()

        mock_update = MockUpdate()

        # Run async tool calls
        import asyncio

        user_info_raw = asyncio.run(_execute_telegram_tool("telegram_get_user_info", {}, mock_update))
        user_info = json.loads(user_info_raw)
        self.assertEqual(user_info["user_id"], 998877)
        self.assertEqual(user_info["username"], "alexsmith")
        self.assertEqual(user_info["full_name"], "Alex Smith")

        dice_res = asyncio.run(_execute_telegram_tool("telegram_send_dice", {"emoji": "🎯"}, mock_update))
        self.assertIn("🎯", dice_res)

        missing_doc_res = asyncio.run(
            _execute_telegram_tool("telegram_send_document", {"file_path": "non_existent_file.pdf"}, mock_update)
        )
        self.assertIn("does not exist", missing_doc_res)

    def test_telegram_bot_commands(self) -> None:
        """Verify registered Telegram menu commands and their descriptions."""
        command_names = [cmd.command for cmd in BOT_COMMANDS]
        self.assertIn("new", command_names)
        self.assertIn("clear", command_names)
        self.assertIn("model", command_names)
        self.assertIn("help", command_names)
        self.assertIn("reset", command_names)
        self.assertIn("start", command_names)
        # Ensure descriptions are not empty
        for cmd in BOT_COMMANDS:
            self.assertTrue(len(cmd.description) > 0)


if __name__ == "__main__":
    unittest.main()
