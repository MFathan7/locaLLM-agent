"""Unit tests for live thinking parser and streaming response generation."""

import unittest
from unittest.mock import MagicMock, patch

from locallm.ui.chat_view import (
    extract_thought_process,
    print_assistant_response,
    stream_assistant_response,
)


class TestLiveChat(unittest.TestCase):
    """Test suite for live thinking and streaming assistant response formatting."""

    def test_extract_thought_process_no_tags(self):
        thought, main = extract_thought_process("Hello world, this is a response.")
        self.assertIsNone(thought)
        self.assertEqual(main, "Hello world, this is a response.")

    def test_extract_thought_process_closed_tag(self):
        text = "<think>\nAnalyzing prompt requirements\n</think>\nHere is your solution."
        thought, main = extract_thought_process(text)
        self.assertEqual(thought, "Analyzing prompt requirements")
        self.assertEqual(main, "Here is your solution.")

    def test_extract_thought_process_unclosed_tag(self):
        text = "<think>\nStill reasoning..."
        thought, main = extract_thought_process(text)
        self.assertEqual(thought, "Still reasoning...")
        self.assertEqual(main, "")

    @patch("locallm.ui.chat_view.console")
    def test_print_assistant_response_with_and_without_thinking(self, mock_console):
        # Without thinking
        print_assistant_response("Direct answer text", model_name="test-model")
        self.assertTrue(mock_console.print.called)

        mock_console.reset_mock()
        # With thinking
        print_assistant_response("<think>Need to calculate</think>Result: 42", model_name="deepseek-r1:8b")
        self.assertTrue(mock_console.print.called)

    @patch("locallm.ui.chat_view.Live")
    @patch("locallm.ui.chat_view.console")
    def test_stream_assistant_response_normal(self, mock_console, mock_live):
        tokens = iter(["Hello", " ", "world", "!"])
        result = stream_assistant_response(tokens, model_name="llama3")
        self.assertEqual(result, "Hello world!")

    @patch("locallm.ui.chat_view.Live")
    @patch("locallm.ui.chat_view.console")
    def test_stream_assistant_response_with_thinking(self, mock_console, mock_live):
        tokens = iter([
            "<think>\n",
            "Let's think step by step.\n",
            "</think>\n",
            "The final answer is 100.",
        ])
        result = stream_assistant_response(tokens, model_name="deepseek-r1")
        self.assertEqual(result, "The final answer is 100.")

    @patch("locallm.ui.chat_view.Live")
    @patch("locallm.ui.chat_view.console")
    def test_stream_assistant_response_empty(self, mock_console, mock_live):
        tokens = iter([])
        result = stream_assistant_response(tokens, model_name="test-model")
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
