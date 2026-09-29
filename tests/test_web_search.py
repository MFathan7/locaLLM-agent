"""Unit tests for real-time web search functionality in locaLLM."""

import unittest
from unittest.mock import MagicMock, patch

from locallm.core.tools import (
    ASSISTANT_TOOLS,
    decode_bing_url,
    describe_tool_action,
    format_live_tool_report,
    perform_web_search,
)


class TestWebSearch(unittest.TestCase):
    """Test suite for autonomous web search capability."""

    def test_search_web_schema_present(self):
        """Verify search_web tool schema is correctly defined in ASSISTANT_TOOLS."""
        names = [t["function"]["name"] for t in ASSISTANT_TOOLS]
        self.assertIn("search_web", names)
        search_tool = next(t for t in ASSISTANT_TOOLS if t["function"]["name"] == "search_web")
        self.assertIn("query", search_tool["function"]["parameters"]["required"])
        self.assertIn("max_results", search_tool["function"]["parameters"]["properties"])

    def test_empty_query_validation(self):
        """Empty query should return a clear error without network request."""
        res = perform_web_search("   ")
        self.assertIn("Error: Search query cannot be empty.", res)

    def test_decode_bing_url(self):
        """Test decoding of base64-encoded redirect URLs from Bing."""
        # Non-bing url returns as is
        raw_url = "https://example.com/page"
        self.assertEqual(decode_bing_url(raw_url), raw_url)

        # Encoded bing u=a1... url
        # Base64 for https://python.org is aHR0cHM6Ly9weXRob24ub3Jn
        encoded_bing = "https://www.bing.com/ck/a?!&&p=123&u=a1aHR0cHM6Ly9weXRob24ub3Jn&ntb=1"
        decoded = decode_bing_url(encoded_bing)
        self.assertEqual(decoded, "https://python.org")

    @patch("httpx.Client.get")
    def test_bing_search_parsing(self, mock_get):
        """Test parsing of Bing HTML search results into structured markdown."""
        sample_html = """
        <html>
          <body>
            <li class="b_algo">
              <h2><a href="https://example.com/item1">First Search Result</a></h2>
              <div class="b_caption"><p>This is the first snippet description.</p></div>
            </li>
            <li class="b_algo">
              <h2><a href="https://example.com/item2">Second Search Result</a></h2>
              <div class="b_caption"><p>This is the second snippet description.</p></div>
            </li>
          </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_html
        mock_get.return_value = mock_response

        output = perform_web_search("test query", max_results=2, provider="bing")
        self.assertIn("Web Search Results for 'test query':", output)
        self.assertIn("First Search Result", output)
        self.assertIn("https://example.com/item1", output)
        self.assertIn("first snippet description", output)
        self.assertIn("Second Search Result", output)

    @patch("httpx.Client.get")
    def test_custom_endpoint_search(self, mock_get):
        """Test custom JSON API endpoint (e.g. SearXNG) formatting."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Custom Search Item",
                    "url": "https://custom.org/doc",
                    "content": "Custom snippet content here.",
                }
            ]
        }
        mock_get.return_value = mock_response

        output = perform_web_search(
            "custom query",
            provider="custom",
            custom_api_url="https://searx.local/search?q={query}&format=json",
        )
        self.assertIn("Custom Search Item", output)
        self.assertIn("https://custom.org/doc", output)
        self.assertIn("Custom snippet content here.", output)

    def test_describe_and_report_search_web(self):
        """Verify spinner description and persistent live report for search_web."""
        desc = describe_tool_action("search_web", {"query": "python asyncio"})
        self.assertIn("searching the web for 'python asyncio'", desc)

        rep = format_live_tool_report("search_web", {"query": "python asyncio"}, "Results...")
        self.assertIn("Searched web:", rep)
        self.assertIn("python asyncio", rep)


if __name__ == "__main__":
    unittest.main()
