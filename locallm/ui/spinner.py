"""Custom spinners and status animations for locaLLM."""

import sys
from contextlib import contextmanager
from typing import Any, Generator, List, Optional
from rich._spinners import SPINNERS
from rich.console import Group
from rich.live import Live
from rich.spinner import Spinner
from rich.status import Status
from rich.text import Text
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
    console_instance: Optional[Any] = None,
) -> Generator[Optional[Status], None, None]:
    """Display rotating square snake spinner while executing a task or waiting for tokens."""
    c = console_instance or console
    if c.is_terminal:
        with c.status(f"[{style}]{text}[/]", spinner="squareSnake") as status:
            yield status
    else:
        yield None


class TaskTracker:
    """Tracks and displays completed task lines, and erases them cleanly when ready to answer."""

    def __init__(self, console_instance: Optional[Any] = None) -> None:
        self.console = console_instance or console
        self.total_lines: int = 0
        self.completed_tasks: List[str] = []

    def print_task(self, report_markup: str) -> None:
        """Print a completed task line to the console and record rendered line count."""
        try:
            rendered = Text.from_markup(report_markup)
            lines = self.console.render_lines(rendered, self.console.options)
            line_count = len(lines)
        except Exception:
            line_count = 1

        self.console.print(report_markup)
        self.total_lines += line_count
        self.completed_tasks.append(report_markup)

    def clear(self) -> None:
        """Erase all printed task lines from the terminal screen."""
        if self.console.is_terminal and self.total_lines > 0:
            try:
                for _ in range(self.total_lines):
                    sys.stdout.write("\033[1A\033[2K\r")
                sys.stdout.flush()
            except Exception:
                pass
            self.total_lines = 0


class AgentProgress:
    """Manages real-time transient task progress lines during agent execution with animated spinner."""

    def __init__(
        self,
        initial_text: str = "locaLLM is thinking...",
        style: str = "bold cyan",
        console_instance: Optional[Any] = None,
    ) -> None:
        self.style = style
        self.current_action = initial_text
        self.completed_tasks: List[str] = []
        self.console = console_instance or console
        self._spinner = Spinner("squareSnake", text=initial_text, style=style)
        self._live: Optional[Live] = None
        self._is_active = False

    @property
    def current_text(self) -> str:
        """Backward-compatible property for current action text."""
        return self.current_action

    def __rich__(self) -> Group:
        items: List[Any] = []
        for task in self.completed_tasks:
            try:
                items.append(Text.from_markup(task))
            except Exception:
                items.append(Text(task))
        items.append(self._spinner)
        return Group(*items)

    def _render(self) -> Group:
        """Return the current renderable group."""
        return self.__rich__()

    def start(self) -> None:
        """Start the live transient task display."""
        if self.console.is_terminal and not self._is_active:
            self._live = Live(
                self,
                console=self.console,
                transient=True,
                refresh_per_second=12.5,
            )
            self._live.start()
            self._is_active = True

    def stop(self) -> None:
        """Stop and erase the transient task display."""
        if self._live and self._is_active:
            self._live.stop()
            self._is_active = False

    def __enter__(self) -> "AgentProgress":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    def update(self, text: str, style: Optional[str] = None) -> None:
        """Update current action text on the animated spinner."""
        self.current_action = text
        if style:
            self.style = style
        self._spinner.update(text=text, style=self.style)
        if self._live and self._is_active:
            self._live.refresh()

    def add_completed_task(self, report_markup: str) -> None:
        """Add a completed task line to the progress view."""
        self.completed_tasks.append(report_markup)
        if self._live and self._is_active:
            self._live.refresh()

    def pause(self) -> None:
        """Temporarily pause the live display (e.g. for user interactive input)."""
        if self._live and self._is_active:
            self._live.stop()

    def resume(self) -> None:
        """Resume the live display with all completed tasks and current action."""
        if self._live and self._is_active:
            self._live.start()
            self._live.refresh()

