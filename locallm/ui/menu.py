"""Main interactive TUI menu and navigation dispatcher."""

import sys
import questionary
from locallm.config import LocaLLMConfig
from locallm.core.ollama_client import OllamaClient
from locallm.modules.agent import run_agent_menu
from locallm.modules.assistant import run_assistant
from locallm.modules.models_manager import run_models_manager
from locallm.modules.service_manager import run_service_manager
from locallm.modules.settings import run_settings
from locallm.modules.telegram_bot import run_telegram_menu
from locallm.modules.whatsapp_bot import run_whatsapp_menu
from locallm.modules.workspace_manager import run_workspace_menu
from locallm.ui.banner import render_banner
from locallm.ui.chat_view import render_application_farewell
from locallm.ui.theme import QUESTIONARY_STYLE, console


def start_main_menu(config: LocaLLMConfig, client: OllamaClient) -> None:
    """Launch top-level interactive console menu loop."""
    while True:
        console.clear()
        render_banner(config, client)

        choice = questionary.select(
            "Main Menu:",
            choices=[
                "Assistant",
                "Workspaces",
                "Integrations",
                "Model Manager",
                "Services",
                "Settings",
                "Exit",
            ],
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
        elif choice == "Services":
            run_service_manager(config)
        elif choice == "Settings":
            run_settings(config)


def _run_integrations_menu(config: LocaLLMConfig, client: OllamaClient) -> None:
    """Submenu for integrations, channels, and autonomous runners."""
    while True:
        console.clear()
        render_banner(config, client)

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

