"""Chat message bubble and scrollable conversation container for locaLLM TUI."""

from typing import Optional
from rich.markdown import Markdown as RichMarkdown
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static


class ChatMessageWidget(Widget):
    """Visual bubble for a single chat message (User, Assistant, or System)."""

    DEFAULT_CSS = """
    ChatMessageWidget {
        height: auto;
        margin: 1 0;
        padding: 0 1;
    }
    """

    content: reactive[str] = reactive("")

    def __init__(
        self,
        role: str,
        header_text: str,
        initial_content: str = "",
        **kwargs,
    ) -> None:
        role_class = "chat-msg-user" if role == "user" else "chat-msg-assistant"
        extra_classes = kwargs.pop("classes", "")
        combined_classes = f"chat-msg {role_class} {extra_classes}".strip()
        super().__init__(classes=combined_classes, **kwargs)
        self.role = role
        self.header_text = header_text
        self.content = initial_content

    def compose(self) -> ComposeResult:
        yield Label(self.header_text, classes="chat-msg-header")
        yield Static(self._format_content(), id="chat-msg-body", classes="chat-msg-body")

    def _format_content(self):
        text = self.content.strip()
        if not text:
            return ""
        try:
            return RichMarkdown(text)
        except Exception:
            return text

    def append_token(self, token: str) -> None:
        """Append streaming token and refresh the rendered message."""
        self.content += token
        try:
            body = self.query_one("#chat-msg-body", Static)
            body.update(self._format_content())
        except Exception:
            pass

    def set_content(self, text: str) -> None:
        """Set full content and refresh."""
        self.content = text
        try:
            body = self.query_one("#chat-msg-body", Static)
            body.update(self._format_content())
        except Exception:
            pass


class ChatScrollContainer(VerticalScroll):
    """Scrollable chat history container with auto-scroll support."""

    DEFAULT_CSS = """
    ChatScrollContainer {
        height: 1fr;
        padding: 0 1;
        overflow-y: auto;
    }
    """

    def scroll_to_latest(self) -> None:
        """Smoothly advance scroll to latest message."""
        self.scroll_end(animate=False)
