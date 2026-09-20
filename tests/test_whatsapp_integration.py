"""Unit tests for WhatsApp integration module, tools, formatting, and whitelist."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import unittest

from locallm.config import LocaLLMConfig
from locallm.core.tools import WHATSAPP_TOOLS
from locallm.modules.whatsapp_bot import (
    execute_whatsapp_tool,
    markdown_to_whatsapp_text,
    normalize_phone_number,
    process_whatsapp_message,
)


class TestWhatsAppIntegration(unittest.TestCase):
    """Test WhatsApp bot helper functions and behaviors."""

    def test_normalize_phone_number(self):
        """Test international prefix formatting and non-digit removal."""
        self.assertEqual(normalize_phone_number("+62 812-3456-7890"), "6281234567890")
        self.assertEqual(normalize_phone_number("08123456789"), "628123456789")
        self.assertEqual(normalize_phone_number("14155552671"), "14155552671")
        self.assertEqual(normalize_phone_number(""), "")

    def test_markdown_to_whatsapp_text(self):
        """Test conversion from markdown bold to WhatsApp formatting."""
        raw = "Hello **world**! Here is # Title and ```print('test')```"
        formatted = markdown_to_whatsapp_text(raw)
        self.assertIn("*world*", formatted)
        self.assertIn("*Title*", formatted)
        self.assertIn("```print('test')```", formatted)

    def test_whatsapp_tools_definitions(self):
        """Verify WhatsApp tools are registered with required fields."""
        tool_names = [t["function"]["name"] for t in WHATSAPP_TOOLS]
        self.assertIn("whatsapp_get_contact_info", tool_names)
        self.assertIn("whatsapp_send_image", tool_names)
        self.assertIn("whatsapp_send_document", tool_names)
        self.assertIn("whatsapp_send_sticker", tool_names)

    def test_whatsapp_whitelist_enforcement(self):
        """Verify unwhitelisted numbers are rejected when whitelist is active."""
        config = LocaLLMConfig(whatsapp_allowed_numbers=["6281234567890"])
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True

        # Unwhitelisted number
        reply = process_whatsapp_message(
            sender_number="628999999999",
            message_text="Hello",
            config=config,
            client=mock_client,
        )
        self.assertIn("not registered in the locaLLM whitelist", reply)
        mock_client.chat_turn.assert_not_called()

    def test_execute_whatsapp_tools(self):
        """Verify WhatsApp tool execution returns descriptive strings."""
        info = execute_whatsapp_tool("whatsapp_get_contact_info", {}, "628123456789")
        self.assertIn("628123456789", info)
        self.assertIn("whatsapp", info)

        doc_res = execute_whatsapp_tool(
            "whatsapp_send_document",
            {"file_path": "non_existent_doc_xyz.pdf"},
            "628123456789",
        )
        self.assertIn("not found on disk", doc_res)


if __name__ == "__main__":
    unittest.main()
