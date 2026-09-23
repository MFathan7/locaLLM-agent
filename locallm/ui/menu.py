"""Main interactive TUI menu and navigation dispatcher."""

import sys
import questionary
from locallm.config import LocaLLMConfig
from locallm.core.openai_client import get_inference_client
from locallm.modules.agent import run_agent_menu
from locallm.modules.assistant import run_assistant
from locallm.modules.models_manager import run_models_manager
from locallm.modules.plugin_menu import run_plugin_menu
from locallm.modules.service_manager import run_service_manager
from locallm.modules.settings import run_settings
from locallm.modules.telegram_bot import run_telegram_menu
from locallm.modules.whatsapp_bot import run_whatsapp_menu
from locallm.modules.workspace_manager import run_workspace_menu
from locallm.ui.banner import render_banner
from locallm.ui.chat_view import render_application_farewell
from locallm.ui.theme import QUESTIONARY_STYLE, apply_active_theme, console
from typing import Any, Optional


def start_main_menu(config: LocaLLMConfig, client: Optional[Any] = None) -> None:
    """Launch top-level interactive console menu loop."""
    while True:
        apply_active_theme(getattr(config, "ui_theme", "cyber_neon"))
        console.clear()
        client = get_inference_client(config)
        render_banner(config, client)

        service_ready = False
        if client and hasattr(client, "is_connected"):
            try:
                service_ready = client.is_connected()
            except Exception:
                service_ready = False

        if not service_ready:
            console.print("[#bbbbbb]Notice: No active LLM service is currently online or configured.[/]")
            console.print("[#bbbbbb]Please configure or start a service in [cyan]Services[/] to unlock full features.[/]\n")
            menu_prompt = "Main Menu (Setup Required):"
            menu_choices = [
                "Services",
                "Settings",
                "Exit",
            ]
        else:
            menu_prompt = "Main Menu:"
            menu_choices = [
                "Assistant",
                "Workspaces",
                "Integrations",
                "Model Manager",
                "Plugins",
                "Services",
                "Settings",
                "Exit",
            ]

        choice = questionary.select(
            menu_prompt,
            choices=menu_choices,
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Exit":
            unloaded = 0
            try:
                unloaded = client.unload_all_models(fallback_model=config.default_model)
            except Exception:
                pass
            render_application_farewell(unloaded_count=unloaded)
            sys.exit(0)

        if choice == "Assistant":
            run_assistant(config, client)
        elif choice == "Workspaces":
            run_workspace_menu(config)
        elif choice == "Integrations":
            _run_integrations_menu(config, client)
        elif choice == "Model Manager":
            run_models_manager(config, client)
        elif choice == "Plugins":
            run_plugin_menu(config)
        elif choice == "Services":
            run_service_manager(config)
        elif choice == "Settings":
            run_settings(config)


def _run_integrations_menu(config: LocaLLMConfig, client: Optional[Any] = None) -> None:
    """Submenu for integrations, channels, and autonomous runners."""
    from locallm.ui.theme import get_theme_palette

    while True:
        console.clear()
        client = get_inference_client(config)
        render_banner(config, client)
        palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))
        console.print(f"[bold {palette.accent}]⟦{palette.icon} INTEGRATIONS & CHANNELS⟧[/]\n")

        choice = questionary.select(
            "Integrations & Channels:",
            choices=[
                "Telegram",
                "WhatsApp",
                "Agent & Automation",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()


        if choice is None or choice == "Back":
            break

        if choice == "Telegram":
            run_telegram_menu(config, client)
        elif choice == "WhatsApp":
            run_whatsapp_menu(config, client)
        elif choice == "Agent & Automation":
            run_agent_menu(config, client)

