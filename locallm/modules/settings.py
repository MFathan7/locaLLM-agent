"""Application settings and configuration editor."""

import questionary
from locallm.config import LocaLLMConfig, save_config, switch_active_backend
from locallm.ui.theme import QUESTIONARY_STYLE, console


def run_settings(config: LocaLLMConfig) -> None:
    """Interactive settings configuration menu."""
    while True:
        ctx_val = getattr(config, "context_window", 8192)
        choice = questionary.select(
            "Settings & Configuration:",
            choices=[
                f"Active Backend (Current: {config.active_backend.upper()})",
                f"Sampling Temperature (Current: {config.temperature})",
                f"Context Window Limit (Current: {ctx_val:,} tokens)",
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
        elif choice.startswith("Sampling Temperature"):
            _edit_temperature(config)
        elif choice.startswith("Context Window Limit"):
            _edit_context_window(config)
        elif choice.startswith("System Prompt"):
            _edit_system_prompt(config)
        elif choice == "Reset to Defaults":
            _reset_defaults(config)


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
        save_config(config)
        console.print("[success]Settings reset to default.[/]\n")
