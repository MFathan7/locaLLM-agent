"""Collapsible interactive Tool Card widget for locaLLM TUI."""

import json
from typing import Any, Dict, Optional
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static

# High contrast spinner frames following AGENTS.md rule
SPINNER_FRAMES = ["▘", "▀", "▝", "▐", "▗", "▄", "▖", "▌"]


class ToolCardWidget(Widget):
    """Collapsible card displaying tool execution status, parameters, and observation."""

    DEFAULT_CSS = """
    ToolCardWidget {
        height: auto;
        margin: 1 0;
        padding: 0 1;
        border: round #555555;
    }
    """

    status: reactive[str] = reactive("running")  # "running", "completed", "failed"
    is_expanded: reactive[bool] = reactive(False)
    spinner_idx: reactive[int] = reactive(0)

    def __init__(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        extra_classes = kwargs.pop("classes", "")
        combined_classes = f"tool-card tool-card-running {extra_classes}".strip()
        super().__init__(classes=combined_classes, **kwargs)
        self.tool_name = tool_name
        self.arguments = arguments or {}
        self.observation: str = ""
        self.duration_sec: float = 0.0
        self._timer = None

    def compose(self) -> ComposeResult:
        yield Label(self._render_header(), id="tool-header", classes="tool-card-header")
        with Vertical(id="tool-details-container", classes="tool-card-details"):
            yield Static(self._render_details(), id="tool-details-content")

    def on_mount(self) -> None:
        # Start spinner animation while running
        if self.status == "running":
            self._timer = self.set_interval(0.12, self._tick_spinner)
        self._update_visibility()

    def _tick_spinner(self) -> None:
        if self.status == "running":
            self.spinner_idx = (self.spinner_idx + 1) % len(SPINNER_FRAMES)
            try:
                self.query_one("#tool-header", Label).update(self._render_header())
            except Exception:
                pass
        else:
            if self._timer:
                self._timer.stop()
                self._timer = None

    def _render_header(self) -> str:
        arg_summary = self._summarize_args()
        if self.status == "running":
            icon = SPINNER_FRAMES[self.spinner_idx]
            return f"{icon} Running: {self.tool_name}({arg_summary})"
        elif self.status == "completed":
            toggle_hint = "▲ [Collapse]" if self.is_expanded else "▼ [Expand]"
            dur_str = f" ({self.duration_sec:.2f}s)" if self.duration_sec > 0 else ""
            return f"✔ {self.tool_name}{dur_str} {toggle_hint}"
        else:
            toggle_hint = "▲ [Collapse]" if self.is_expanded else "▼ [Expand]"
            return f"✖ Failed: {self.tool_name} {toggle_hint}"

    def _summarize_args(self) -> str:
        if not self.arguments:
            return ""
        items = []
        for k, v in list(self.arguments.items())[:2]:
            val_str = str(v)
            if len(val_str) > 30:
                val_str = val_str[:27] + "..."
            items.append(f"{k}={repr(val_str)}")
        return ", ".join(items)

    def _render_details(self) -> str:
        parts = []
        if self.arguments:
            parts.append(f"**Arguments:**\n```json\n{json.dumps(self.arguments, indent=2)}\n```")
        if self.observation:
            obs_preview = self.observation
            if len(obs_preview) > 2000:
                obs_preview = obs_preview[:2000] + f"\n... [Truncated {len(self.observation)} characters]"
            parts.append(f"**Observation:**\n```\n{obs_preview}\n```")
        return "\n\n".join(parts) if parts else "No execution details."

    def complete(self, observation: str, success: bool = True, duration: float = 0.0) -> None:
        """Mark tool execution as completed and update UI state."""
        self.status = "completed" if success else "failed"
        self.observation = observation
        self.duration_sec = duration
        if self._timer:
            self._timer.stop()
            self._timer = None

        self.remove_class("tool-card-running")
        self.add_class("tool-card-completed" if success else "tool-card-failed")

        try:
            self.query_one("#tool-header", Label).update(self._render_header())
            self.query_one("#tool-details-content", Static).update(self._render_details())
        except Exception:
            pass

    def on_click(self) -> None:
        """Toggle expanded view when card is clicked."""
        if self.status != "running":
            self.is_expanded = not self.is_expanded
            self._update_visibility()
            try:
                self.query_one("#tool-header", Label).update(self._render_header())
            except Exception:
                pass

    def _update_visibility(self) -> None:
        try:
            details = self.query_one("#tool-details-container")
            details.display = self.is_expanded
        except Exception:
            pass
