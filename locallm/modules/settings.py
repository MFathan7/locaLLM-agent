"""Application settings and configuration editor."""

import questionary
from locallm.config import LocaLLMConfig, save_config, switch_active_backend
from locallm.ui.theme import (
    QUESTIONARY_STYLE,
    apply_active_theme,
    console,
    get_theme_palette,
    list_available_themes,
)


def run_settings(config: LocaLLMConfig) -> None:
    """Interactive settings configuration menu."""
    while True:
        ctx_val = getattr(config, "context_window", 8192)
        search_prov = getattr(config, "search_provider", "auto")
        theme_pal = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))
        ui_mode_val = "Modern TUI" if getattr(config, "ui_mode", "classic") == "modern" else "Default CLI"
        max_steps_val = getattr(config, "agent_max_steps", 25)
        choice = questionary.select(
            "Settings & Configuration:",
            choices=[
                f"Active Backend (Current: {config.active_backend.upper()})",
                f"UI Mode (Current: {ui_mode_val})",
                f"UI Theme (Current: {theme_pal.name})",
                f"Sampling Temperature (Current: {config.temperature})",
                f"Context Window Limit (Current: {ctx_val:,} tokens)",
                f"Agent Max Steps (Current: {max_steps_val} steps)",
                f"Web Search Provider (Current: {search_prov.upper()})",
                f"System Prompt (Current: {config.system_prompt[:30]}...)",
                "Reset to Defaults",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice.startswith("Active Backend"):
            _switch_active_backend(config)
        elif choice.startswith("UI Mode"):
            _switch_ui_mode(config)
        elif choice.startswith("UI Theme"):
            _switch_ui_theme(config)
        elif choice.startswith("Sampling Temperature"):
            _edit_temperature(config)
        elif choice.startswith("Context Window Limit"):
            _edit_context_window(config)
        elif choice.startswith("Agent Max Steps"):
            _edit_agent_max_steps(config)
        elif choice.startswith("Web Search Provider"):
            _configure_search_provider(config)
        elif choice.startswith("System Prompt"):
            _edit_system_prompt(config)
        elif choice == "Reset to Defaults":
            _reset_defaults(config)



def _configure_search_provider(config: LocaLLMConfig) -> None:
    """Configure web search provider and custom endpoint URL."""
    provider_choice = questionary.select(
        "Choose Web Search Provider:",
        choices=[
            "Auto (DuckDuckGo with Bing Fallback)",
            "Bing (Fast, Global, High Availability)",
            "DuckDuckGo (Direct HTML / API)",
            "Custom (Self-Hosted SearXNG or Proxy URL)",
            "Cancel",
        ],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not provider_choice or provider_choice == "Cancel":
        return

    if provider_choice.startswith("Auto"):
        config.search_provider = "auto"
    elif provider_choice.startswith("Bing"):
        config.search_provider = "bing"
    elif provider_choice.startswith("DuckDuckGo"):
        config.search_provider = "duckduckgo"
    elif provider_choice.startswith("Custom"):
        config.search_provider = "custom"
        api_url = questionary.text(
            "Enter custom search endpoint URL (use {query} placeholder, e.g. https://searx.example.com/search?q={query}&format=json):",
            default=getattr(config, "search_api_url", ""),
            style=QUESTIONARY_STYLE,
        ).ask()
        if api_url is not None:
            config.search_api_url = api_url.strip()

    save_config(config)
    console.print(f"[success]Web search provider configured: {config.search_provider.upper()}[/]\n")


def _switch_active_backend(config: LocaLLMConfig) -> None:
    """Choose active inference backend from Ollama and registered custom platforms."""
    choices = ["Ollama"]
    for p in config.custom_platforms:
        choices.append(p.name)
    choices.extend(["Add Custom Platform", "Cancel"])

    chosen = questionary.select(
        "Choose Active Inference Backend:",
        choices=choices,
        style=QUESTIONARY_STYLE,
    ).ask()

    if not chosen or chosen == "Cancel":
        return

    if chosen == "Add Custom Platform":
        from locallm.modules.service_manager import _add_custom_platform_wizard
        _add_custom_platform_wizard(config)
    else:
        ok, msg = switch_active_backend(config, chosen)
        if ok:
            console.print(f"[success]{msg}[/]\n")
        else:
            console.print(f"[danger]{msg}[/]\n")


def _edit_temperature(config: LocaLLMConfig) -> None:
    temp_str = questionary.text(
        "Enter temperature (0.0 to 2.0):",
        default=str(config.temperature),
        style=QUESTIONARY_STYLE,
    ).ask()
    try:
        val = float(temp_str)
        if 0.0 <= val <= 2.0:
            config.temperature = val
            save_config(config)
            console.print("[success]Temperature updated.[/]\n")
        else:
            console.print("[warning]Value must be between 0.0 and 2.0.[/]\n")
    except ValueError:
        console.print("[danger]Invalid numerical value.[/]\n")


def _edit_context_window(config: LocaLLMConfig) -> None:
    current_ctx = getattr(config, "context_window", 8192)
    ctx_str = questionary.text(
        "Enter context window limit in tokens (e.g. 4096, 8192, 16384, 32768):",
        default=str(current_ctx),
        style=QUESTIONARY_STYLE,
    ).ask()
    try:
        val = int(ctx_str)
        if 512 <= val <= 262144:
            config.context_window = val
            save_config(config)
            console.print(f"[success]Context window updated to {val:,} tokens.[/]\n")
        else:
            console.print("[warning]Value must be between 512 and 262,144.[/]\n")
    except (ValueError, TypeError):
        console.print("[danger]Invalid numerical integer value.[/]\n")


def _edit_system_prompt(config: LocaLLMConfig) -> None:
    new_prompt = questionary.text(
        "Enter default system prompt:",
        default=config.system_prompt,
        style=QUESTIONARY_STYLE,
    ).ask()
    if new_prompt and new_prompt.strip():
        config.system_prompt = new_prompt.strip()
        save_config(config)
        console.print("[success]System prompt updated.[/]\n")


def _reset_defaults(config: LocaLLMConfig) -> None:
    confirm = questionary.confirm(
        "Reset all settings to default values?",
        default=False,
        style=QUESTIONARY_STYLE,
    ).ask()
    if confirm:
        default_cfg = LocaLLMConfig()
        config.active_backend = default_cfg.active_backend
        config.ollama_host = default_cfg.ollama_host
        config.custom_platforms = []
        config.default_model = default_cfg.default_model
        config.temperature = default_cfg.temperature
        config.context_window = default_cfg.context_window
        config.system_prompt = default_cfg.system_prompt
        config.telegram_token = default_cfg.telegram_token
        config.agent_auto_approve_commands = default_cfg.agent_auto_approve_commands
        config.agent_permission_policy = default_cfg.agent_permission_policy
        config.agent_max_steps = default_cfg.agent_max_steps
        config.ui_theme = default_cfg.ui_theme
        save_config(config)
        apply_active_theme(config.ui_theme)
        console.print("[success]Settings reset to default.[/]\n")


def _edit_agent_max_steps(config: LocaLLMConfig) -> None:
    """Interactively configure maximum agent reasoning and execution steps."""
    curr = getattr(config, "agent_max_steps", 25)
    val_str = questionary.text(
        "Enter maximum agent execution steps (1 to 100):",
        default=str(curr),
        style=QUESTIONARY_STYLE,
    ).ask()
    if val_str is None:
        return
    try:
        val = int(val_str.strip())
        if 1 <= val <= 100:
            config.agent_max_steps = val
            save_config(config)
            console.print(f"[success]Agent max steps updated to: [bold cyan]{val}[/][/]\n")
        else:
            console.print("[warning]Value must be between 1 and 100.[/]\n")
    except ValueError:
        console.print("[danger]Invalid integer value.[/]\n")


def _switch_ui_theme(config: LocaLLMConfig) -> None:
    """Interactively select and preview a UI theme."""
    themes = list_available_themes()
    current_key = getattr(config, "ui_theme", "cyber_neon")
    choices = [
        f"{name} ({desc})" + (" [Active]" if key == current_key else "")
        for key, name, desc in themes
    ]
    choices.append("Cancel")

    chosen = questionary.select(
        "Choose UI Theme:",
        choices=choices,
        style=QUESTIONARY_STYLE,
    ).ask()

    if not chosen or chosen == "Cancel":
        return

    for key, name, _ in themes:
        if chosen.startswith(name):
            config.ui_theme = key
            save_config(config)
            apply_active_theme(key)
            console.print(f"[success]UI Theme switched to {name}![/]\n")
            break


def _switch_ui_mode(config: LocaLLMConfig) -> None:
    """Interactively select between Default CLI and Modern Reactive TUI."""
    curr_mode = getattr(config, "ui_mode", "classic")
    current_label = "Modern TUI" if curr_mode == "modern" else "Default CLI"

    choices = [
        "Default CLI (Traditional scrolling terminal)" + (" [Active]" if curr_mode == "classic" else ""),
        "Modern TUI (Reactive full-screen split-pane)" + (" [Active]" if curr_mode == "modern" else ""),
        "Cancel",
    ]

    chosen = questionary.select(
        f"Select Interface Style (Current: {current_label}):",
        choices=choices,
        style=QUESTIONARY_STYLE,
    ).ask()

    if not chosen or chosen == "Cancel":
        return

    if "Modern TUI" in chosen:
        config.ui_mode = "modern"
        save_config(config)
        console.print("[success]Interface style set to Modern TUI![/]\n")
    elif "Default CLI" in chosen:
        config.ui_mode = "classic"
        save_config(config)
        console.print("[success]Interface style set to Default CLI![/]\n")

    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()

