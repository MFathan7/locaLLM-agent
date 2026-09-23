"""Responsive input box and submission trigger for locaLLM TUI."""

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input


class PromptBox(Widget):
    """User prompt bar containing multi-line capable input and send button."""

    DEFAULT_CSS = """
    PromptBox {
        height: auto;
        dock: bottom;
        padding: 0 1 1 1;
        layout: horizontal;
    }
    """

    class Submitted(Message):
        """Event posted when user submits a message."""

        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    def __init__(self, placeholder: str = "Type message or /help, /stats, /clear, /theme...", **kwargs) -> None:
        kwargs.setdefault("id", "prompt-container")
        super().__init__(**kwargs)
        self.placeholder = placeholder
        self._history = []
        self._history_idx = -1

    def compose(self) -> ComposeResult:
        yield Input(
            placeholder=self.placeholder,
            id="prompt-input",
        )
        yield Button("Send", id="send-button", variant="primary")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Triggered when Enter key is pressed in the input field."""
        self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Triggered when Send button is clicked."""
        if event.button.id == "send-button":
            self._submit()

    def _submit(self) -> None:
        try:
            inp = self.query_one("#prompt-input", Input)
            val = inp.value.strip()
            if val:
                self._history.append(val)
                self._history_idx = len(self._history)
                inp.value = ""
                self.post_message(self.Submitted(val))
        except Exception:
            pass

    def focus_input(self) -> None:
        """Give keyboard focus to the prompt input."""
        try:
            self.query_one("#prompt-input", Input).focus()
        except Exception:
            pass
