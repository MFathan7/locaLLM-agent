"""Configuration manager for locaLLM."""

import json
from pathlib import Path
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class CustomPlatformConfig(BaseModel):
    """Configuration for an OpenAI-compatible custom platform."""

    name: str = Field(description="Unique platform name, e.g. 'vLLM', 'LocalAI'")
    api_base: str = Field(
        default="http://127.0.0.1:8000/v1",
        description="OpenAI-compatible base API URL",
    )
    api_key: str = Field(
        default="",
        description="Optional API key for authentication",
    )
    default_model: str = Field(
        default="",
        description="Optional default model for this platform",
    )


class LocaLLMConfig(BaseModel):
    """Application configuration schema."""

    active_backend: str = Field(
        default="ollama",
        description="Active backend provider: 'ollama' or custom platform name",
    )
    ollama_host: str = Field(
        default="http://127.0.0.1:11434",
        description="Ollama API base URL",
    )
    ollama_model: str = Field(
        default="gemma4:12b",
        description="Saved default active model for Ollama",
    )
    custom_platforms: List[CustomPlatformConfig] = Field(
        default_factory=list,
        description="User-configured custom OpenAI-compatible platforms",
    )
    default_model: str = Field(
        default="gemma4:12b",
        description="Default active model identifier",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    context_window: int = Field(
        default=8192,
        ge=512,
        le=262144,
        description="Context window limit in tokens (default: 8192)",
    )
    system_prompt: str = Field(
        default="You are locaLLM, a helpful, fast, and intelligent local AI assistant.",
        description="Default system prompt instructions",
    )
    telegram_token: str = Field(
        default="",
        description="Telegram bot token obtained from @BotFather",
    )
    telegram_allowed_users: List[int] = Field(
        default_factory=list,
        description="Optional list of Telegram User IDs allowed to access the bot",
    )
    whatsapp_enabled: bool = Field(
        default=False,
        description="Whether WhatsApp bot integration is enabled",
    )
    whatsapp_allowed_numbers: List[str] = Field(
        default_factory=list,
        description="Whitelist of allowed WhatsApp sender phone numbers e.g. ['628123456789']",
    )
    whatsapp_session_dir: str = Field(
        default="",
        description="Optional custom directory for WhatsApp session keys and pairing data",
    )
    agent_auto_approve_commands: bool = Field(
        default=False,
        description="Whether autonomous agent runs commands without prompt",
    )
    agent_permission_policy: str = Field(
        default="ask",
        description="Agent permission policy for mutating tools: 'always_allow', 'ask', 'deny'",
    )
    active_workspace: str = Field(
        default="default",
        description="Currently active workspace identifier",
    )
    search_provider: str = Field(
        default="auto",
        description="Search provider for web search: 'auto', 'bing', 'duckduckgo', or 'custom'",
    )
    search_api_url: str = Field(
        default="",
        description="Optional custom search endpoint URL (e.g. self-hosted SearXNG or proxy)",
    )
    ui_theme: str = Field(
        default="cyber_neon",
        description="Active console UI theme: 'cyber_neon', 'tokyo_night', 'monokai', 'matrix', or 'nordic_frost'",
    )



def get_config_dir() -> Path:
    """Return user configuration directory path."""
    config_dir = Path.home() / ".locallm"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file_path() -> Path:
    """Return the absolute path to config.json."""
    return get_config_dir() / "config.json"


def load_config() -> LocaLLMConfig:
    """Load configuration from disk or create default if absent."""
    config_path = get_config_file_path()
    if not config_path.exists():
        config = LocaLLMConfig()
        save_config(config)
        return config

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            # Migrate away from legacy lmstudio if present
            if str(data.get("active_backend", "")).lower() == "lmstudio":
                data["active_backend"] = "ollama"
            data.pop("lmstudio_host", None)
            if "ollama_model" not in data and "default_model" in data:
                data["ollama_model"] = data["default_model"]
            if "agent_permission_policy" not in data:
                if data.get("agent_auto_approve_commands"):
                    data["agent_permission_policy"] = "always_allow"
                else:
                    data["agent_permission_policy"] = "ask"
            cfg = LocaLLMConfig(**data)
            # Ensure active_backend is valid
            if cfg.active_backend.lower() != "ollama":
                plat = get_custom_platform(cfg, cfg.active_backend)
                if not plat:
                    cfg.active_backend = "ollama"
                    cfg.default_model = cfg.ollama_model
                    save_config(cfg)
            return cfg
    except Exception:
        # Fallback to defaults on corruption
        return LocaLLMConfig()


def save_config(config: LocaLLMConfig) -> None:
    """Persist configuration object to disk."""
    config_path = get_config_file_path()
    with open(config_path, "w", encoding="utf-8") as file:
        file.write(config.model_dump_json(indent=2))


def get_custom_platform(config: LocaLLMConfig, name: str) -> Optional[CustomPlatformConfig]:
    """Find a custom platform configuration by name (case-insensitive)."""
    target = name.strip().lower()
    for p in config.custom_platforms:
        if p.name.strip().lower() == target:
            return p
    return None


def add_custom_platform(config: LocaLLMConfig, platform: CustomPlatformConfig) -> Tuple[bool, str]:
    """Add a new custom OpenAI-compatible platform configuration."""
    clean_name = platform.name.strip()
    if not clean_name:
        return False, "Platform name cannot be empty."

    if clean_name.lower() == "ollama":
        return False, f"Platform name '{clean_name}' is reserved."

    if get_custom_platform(config, clean_name) is not None:
        return False, f"Platform '{clean_name}' already exists."

    config.custom_platforms.append(platform)
    save_config(config)
    return True, f"Platform '{clean_name}' added successfully."


def switch_active_backend(config: LocaLLMConfig, backend_name: str) -> Tuple[bool, str]:
    """Switch active inference backend and synchronize model selection per platform."""
    target = backend_name.strip()
    target_lower = target.lower()
    curr_backend = config.active_backend.strip().lower()

    # 1. Persist current active model to current backend before switching
    if curr_backend == "ollama":
        config.ollama_model = config.default_model
    else:
        curr_plat = get_custom_platform(config, curr_backend)
        if curr_plat:
            curr_plat.default_model = config.default_model

    # 2. Switch to Ollama
    if target_lower == "ollama":
        config.active_backend = "ollama"
        config.default_model = config.ollama_model or "gemma4:12b"
        save_config(config)
        return True, f"Active backend switched to: Ollama (Model: {config.default_model})"

    # 3. Switch to Custom Platform
    platform = get_custom_platform(config, target)
    if not platform:
        return False, f"Platform '{target}' not found."

    config.active_backend = platform.name

    # If platform already has a preferred model, use it
    if platform.default_model and platform.default_model.strip():
        config.default_model = platform.default_model.strip()
    else:
        # Discover first available model from platform if endpoint is reachable
        try:
            from locallm.core.openai_client import OpenAIClient
            client = OpenAIClient(api_base=platform.api_base, api_key=platform.api_key)
            if client.is_connected(max_cache_age=0.0):
                models = client.list_models()
                if models:
                    first_id = models[0].get("id") or models[0].get("name", "")
                    if first_id:
                        platform.default_model = first_id
                        config.default_model = first_id
        except Exception:
            pass

    save_config(config)
    return True, f"Active backend switched to: {platform.name} (Model: {config.default_model})"


def remove_custom_platform(config: LocaLLMConfig, name: str) -> Tuple[bool, str]:
    """Remove a custom platform configuration by name, cleaning up model references."""
    clean_name = name.strip()
    existing = get_custom_platform(config, clean_name)
    if not existing:
        return False, f"Platform '{clean_name}' not found."

    deleted_model = existing.default_model.strip()
    was_active = (config.active_backend.strip().lower() == clean_name.lower())
    had_model = (bool(deleted_model) and config.default_model.strip() == deleted_model)

    config.custom_platforms = [p for p in config.custom_platforms if p.name.strip().lower() != clean_name.lower()]

    # If the removed platform was active or its model was selected, fallback to Ollama cleanly
    if was_active or had_model:
        config.active_backend = "ollama"
        config.default_model = config.ollama_model or "gemma4:12b"
        try:
            from locallm.core.ollama_client import OllamaClient
            ollama_client = OllamaClient(base_url=config.ollama_host)
            if ollama_client.is_connected():
                models = ollama_client.list_models()
                model_names = [m.get("name") for m in models if m.get("name")]
                if model_names and config.default_model not in model_names:
                    config.default_model = model_names[0]
                    config.ollama_model = model_names[0]
        except Exception:
            pass

    save_config(config)
    msg = f"Platform '{clean_name}' removed successfully."
    if was_active or had_model:
        msg += f" Fallback to Ollama with model '{config.default_model}'."
    return True, msg


def update_custom_platform(
    config: LocaLLMConfig,
    name: str,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    default_model: Optional[str] = None,
) -> Tuple[bool, str]:
    """Update settings for an existing custom platform."""
    clean_name = name.strip()
    platform = get_custom_platform(config, clean_name)
    if not platform:
        return False, f"Platform '{clean_name}' not found."

    if api_base is not None and api_base.strip():
        platform.api_base = api_base.strip()
    if api_key is not None:
        platform.api_key = api_key.strip()
    if default_model is not None:
        platform.default_model = default_model.strip()
        if config.active_backend.strip().lower() == clean_name.lower():
            config.default_model = platform.default_model

    save_config(config)
    return True, f"Platform '{clean_name}' updated successfully."
