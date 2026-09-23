"""Interactive Integrations view (Telegram, WhatsApp, Agent) for locaLLM TUI."""

from typing import Any
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static
from locallm.config import LocaLLMConfig, save_config


class RunAgentTaskRequested(Message):
    """Event posted when user submits an autonomous agent task from the Integrations tab."""

    def __init__(self, task_instruction: str) -> None:
        super().__init__()
        self.task_instruction = task_instruction


class IntegrationsView(Widget):
    """View managing external channels (Telegram, WhatsApp) and autonomous ReAct agent."""

    DEFAULT_CSS = """
    IntegrationsView {
        height: 100%;
        padding: 1 2;
    }

    #integrations-scroll {
        height: 1fr;
        overflow-y: auto;
    }

    .integration-row {
        layout: horizontal;
        height: auto;
        margin-top: 1;
    }

    .integration-input {
        width: 1fr;
        margin-right: 1;
    }
    """

    def __init__(self, config: LocaLLMConfig, client: Any, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config
        self.client = client

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="integrations-scroll"):
            with Vertical(classes="stat-box"):
                yield Label("✦ AUTONOMOUS AGENT RUNNER ✦", classes="stat-title")
                yield Label(
                    f"• Permission Policy: [bold cyan]{getattr(self.config, 'agent_permission_policy', 'ask')}[/]  "
                    f"• Max Steps: [bold cyan]{getattr(self.config, 'agent_max_steps', 25)}[/]",
                    classes="stat-row",
                )
                yield Label("Run multi-step autonomous task with filesystem, shell, and web tools:", classes="stat-row")
                with Horizontal(classes="integration-row"):
                    yield Input(
                        placeholder="e.g. Scrape latest release of uv and write summary report to ./report.md",
                        id="input-agent-task",
                        classes="integration-input",
                    )
                    yield Button("Launch Task in Chat", id="btn-launch-agent-task", variant="primary")

            with Vertical(classes="stat-box"):
                yield Label("TELEGRAM BOT INTEGRATION", classes="stat-title")
                token_preview = f"Configured (ends with ...{self.config.telegram_token[-4:]})" if self.config.telegram_token else "[yellow]Not Configured[/]"
                yield Label(f"• Bot Token: {token_preview}", id="lbl-telegram-token-status", classes="stat-row")
                yield Label(f"• Whitelist Users: {self.config.telegram_allowed_users or 'All users'}", classes="stat-row")
                with Horizontal(classes="integration-row"):
                    yield Input(placeholder="Paste BotFather Token here...", id="input-tg-token", classes="integration-input", password=True)
                    yield Button("Save Token", id="btn-save-tg-token", variant="success")
                yield Label("", id="lbl-tg-status")

            with Vertical(classes="stat-box"):
                yield Label("WHATSAPP BOT INTEGRATION", classes="stat-title")
                wa_status = "[bold green]ENABLED[/]" if getattr(self.config, "whatsapp_enabled", False) else "[dim]DISABLED[/]"
                yield Label(f"• Integration State: {wa_status}", id="lbl-wa-state", classes="stat-row")
                yield Label(f"• Whitelist Numbers: {self.config.whatsapp_allowed_numbers or 'None configured'}", classes="stat-row")
                with Horizontal(classes="integration-row"):
                    toggle_label = "Disable WhatsApp" if getattr(self.config, "whatsapp_enabled", False) else "Enable WhatsApp"
                    yield Button(toggle_label, id="btn-toggle-wa", variant="default")

    def on_mount(self) -> None:
        self.refresh_integrations()

    def refresh_integrations(self) -> None:
        """Update live status of Telegram and WhatsApp configurations."""
        try:
            token_preview = f"Configured (ends with ...{self.config.telegram_token[-4:]})" if self.config.telegram_token else "[yellow]Not Configured[/]"
            self.query_one("#lbl-telegram-token-status", Label).update(f"• Bot Token: {token_preview}")
            wa_status = "[bold green]ENABLED[/]" if getattr(self.config, "whatsapp_enabled", False) else "[dim]DISABLED[/]"
            self.query_one("#lbl-wa-state", Label).update(f"• Integration State: {wa_status}")
            new_btn_lbl = "Disable WhatsApp" if getattr(self.config, "whatsapp_enabled", False) else "Enable WhatsApp"
            self.query_one("#btn-toggle-wa", Button).label = new_btn_lbl
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-save-tg-token":
            self._handle_save_tg_token()
        elif btn_id == "btn-toggle-wa":
            self._handle_toggle_wa()
        elif btn_id == "btn-launch-agent-task":
            self._handle_launch_agent()

    def _handle_save_tg_token(self) -> None:
        inp = self.query_one("#input-tg-token", Input)
        val = inp.value.strip()
        if not val:
            self.query_one("#lbl-tg-status", Label).update("[red]Token cannot be empty.[/]")
            return

        self.config.telegram_token = val
        save_config(self.config)
        inp.value = ""
        self.query_one("#lbl-tg-status", Label).update("[green]✔ Telegram bot token saved![/]")
        token_preview = f"Configured (ends with ...{val[-4:]})"
        self.query_one("#lbl-telegram-token-status", Label).update(f"• Bot Token: {token_preview}")

    def _handle_toggle_wa(self) -> None:
        curr = getattr(self.config, "whatsapp_enabled", False)
        self.config.whatsapp_enabled = not curr
        save_config(self.config)
        new_state = "[bold green]ENABLED[/]" if self.config.whatsapp_enabled else "[dim]DISABLED[/]"
        self.query_one("#lbl-wa-state", Label).update(f"• Integration State: {new_state}")
        new_btn_lbl = "Disable WhatsApp" if self.config.whatsapp_enabled else "Enable WhatsApp"
        self.query_one("#btn-toggle-wa", Button).label = new_btn_lbl

    def _handle_launch_agent(self) -> None:
        inp = self.query_one("#input-agent-task", Input)
        task_text = inp.value.strip()
        if task_text:
            inp.value = ""
            self.post_message(RunAgentTaskRequested(task_text))
