"""Custom spinners and status animations for locaLLM."""

from contextlib import contextmanager
from typing import Generator, Optional
from rich._spinners import SPINNERS
from rich.status import Status
from locallm.ui.theme import console

# Register rotating square snake spinner
# Clockwise perimeter loop: Top-Left -> Top -> Top-Right -> Right -> Bottom-Right -> Bottom -> Bottom-Left -> Left
SPINNERS["squareSnake"] = {
    "interval": 80,
    "frames": [
        "▘",
        "▀",
        "▝",
        "▐",
        "▗",
        "▄",
        "▖",
        "▌",
    ],
}


@contextmanager
def thinking_spinner(
    text: str = "locaLLM is thinking...",
    style: str = "bold cyan",
) -> Generator[Optional[Status], None, None]:
    """Display rotating square snake spinner while executing a task or waiting for tokens."""
    if console.is_terminal:
        with console.status(f"[{style}]{text}[/]", spinner="squareSnake") as status:
            yield status
    else:
        yield None
