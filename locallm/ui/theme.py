"""Theme registry and dynamic terminal styling engine for locaLLM."""

from dataclasses import dataclass
import sys
from typing import Any, Dict, List, Optional, Tuple
from questionary import Style
from rich import box
from rich.console import Console
from rich.theme import Theme

# Ensure UTF-8 console output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


@dataclass(frozen=True)
class ThemePalette:
    """Design tokens and color palette for a console UI theme."""

    key: str
    name: str
    description: str
    primary: str        # e.g. '#00f0ff' (Primary brand / commands / highlight)
    accent: str         # e.g. '#ff007f' (Secondary highlight / header tag)
    success: str        # e.g. '#00ff66' (Success / healthy / active)
    warning: str        # e.g. '#ffe600' (Warning / caution / spillover)
    danger: str         # e.g. '#ff3366' (Error / failed / offline)
    dim: str            # e.g. '#aaaaaa' (Muted descriptions / borders)
    border_style: str   # Rich border color name, e.g. 'magenta', 'cyan', 'blue'
    icon: str           # ASCII/Unicode theme icon (e.g. '⚡', '◈', '★', 'λ', '❄')
    box_style: Any      # Rich box style (box.DOUBLE, box.ROUNDED, box.HEAVY, box.SQUARE)
    prompt_symbol: str  # Prompt symbol (e.g. '❯', '›', '»', '$')
    user_prefix: str    # User prompt label (e.g. '▲ You', '◆ You', '■ You', '>>> You', '• You')
    ai_prefix: str      # AI response label (e.g. '⚡ locaLLM', '◈ locaLLM', '★ locaLLM', 'λ locaLLM', '❄ locaLLM')
    badge: str          # Theme badge (e.g. '⟦⚡ CYBER⟧', '⟦◈ TOKYO⟧', '⟦★ RETRO⟧', '⟦λ MATRIX⟧', '⟦❄ FROST⟧')


THEME_DEFINITIONS: Dict[str, ThemePalette] = {
    "cyber_neon": ThemePalette(
        key="cyber_neon",
        name="Cyber Neon",
        description="Hermes / Cyberpunk aesthetic with electric cyan and neon magenta",
        primary="#00f0ff",
        accent="#ff007f",
        success="#00ff66",
        warning="#ffe600",
        danger="#ff3366",
        dim="#8892b0",
        border_style="magenta",
        icon="⚡",
        box_style=box.DOUBLE,
        prompt_symbol="❯",
        user_prefix="▲ You",
        ai_prefix="⚡ locaLLM",
        badge="⟦⚡ CYBER⟧",
    ),
    "tokyo_night": ThemePalette(
        key="tokyo_night",
        name="Tokyo Night",
        description="Modern sleek IDE aesthetic with slate blue and soft amethyst",
        primary="#7aa2f7",
        accent="#bb9af7",
        success="#73daca",
        warning="#e0af68",
        danger="#f7768e",
        dim="#565f89",
        border_style="blue",
        icon="◈",
        box_style=box.ROUNDED,
        prompt_symbol="›",
        user_prefix="◆ You",
        ai_prefix="◈ locaLLM",
        badge="⟦◈ TOKYO⟧",
    ),
    "monokai": ThemePalette(
        key="monokai",
        name="Monokai",
        description="Warm retro-arcade synthwave with sunset amber and coral pink",
        primary="#ffd866",
        accent="#ff6188",
        success="#a9dc76",
        warning="#fc9867",
        danger="#ff4060",
        dim="#727072",
        border_style="yellow",
        icon="★",
        box_style=box.HEAVY,
        prompt_symbol="»",
        user_prefix="■ You",
        ai_prefix="★ locaLLM",
        badge="⟦★ RETRO⟧",
    ),
    "matrix": ThemePalette(
        key="matrix",
        name="Matrix",
        description="Classic DEFCON hacker terminal with phosphor green and white",
        primary="#39ff14",
        accent="#ffffff",
        success="#00ff41",
        warning="#ffb000",
        danger="#ff0033",
        dim="#008f11",
        border_style="green",
        icon="λ",
        box_style=box.SQUARE,
        prompt_symbol="$",
        user_prefix=">>> You",
        ai_prefix="λ locaLLM",
        badge="⟦λ MATRIX⟧",
    ),
    "nordic_frost": ThemePalette(
        key="nordic_frost",
        name="Nordic Frost",
        description="Clean Scandinavian aesthetic with arctic cyan and polar blue",
        primary="#88c0d0",
        accent="#81a1c1",
        success="#a3be8c",
        warning="#ebcb8b",
        danger="#bf616a",
        dim="#4c566a",
        border_style="cyan",
        icon="❄",
        box_style=box.ROUNDED,
        prompt_symbol="›",
        user_prefix="• You",
        ai_prefix="❄ locaLLM",
        badge="⟦❄ FROST⟧",
    ),
}

DEFAULT_THEME_KEY = "cyber_neon"
_CURRENT_THEME_KEY = DEFAULT_THEME_KEY


def get_theme_palette(name: Optional[str] = None) -> ThemePalette:
    """Return the ThemePalette object for a theme key (defaults to active)."""
    target = (name or _CURRENT_THEME_KEY or DEFAULT_THEME_KEY).strip().lower()
    return THEME_DEFINITIONS.get(target, THEME_DEFINITIONS[DEFAULT_THEME_KEY])


def build_rich_theme(palette: ThemePalette) -> Theme:
    """Construct Rich theme mappings using theme tokens."""
    return Theme({
        "info": palette.primary,
        "warning": palette.warning,
        "danger": f"bold {palette.danger}",
        "success": f"bold {palette.success}",
        "highlight": f"bold {palette.accent}",
        "dimmed": f"dim {palette.dim}",
        "model": f"bold {palette.primary}",
        "vram_ok": f"bold {palette.success}",
        "vram_warn": f"bold {palette.warning}",
        "vram_bad": f"bold {palette.danger}",
    })


def build_questionary_style(palette: ThemePalette) -> Style:
    """Construct a clean, high-contrast Questionary style without emojis."""
    return Style([
        ("qmark", f"fg:{palette.primary} bold"),
        ("question", "bold fg:#ffffff"),
        ("answer", f"fg:{palette.success} bold"),
        ("pointer", f"fg:{palette.accent} bold"),
        ("highlighted", f"fg:{palette.primary} bold"),
        ("selected", f"fg:{palette.success}"),
        ("separator", f"fg:{palette.dim}"),
        ("instruction", f"fg:{palette.dim} italic"),
        ("text", "fg:#dddddd"),
        ("disabled", f"fg:{palette.dim} italic"),
    ])


def list_available_themes() -> List[Tuple[str, str, str]]:
    """Return list of (key, display_name, description) for all themes."""
    return [
        (p.key, p.name, p.description)
        for p in THEME_DEFINITIONS.values()
    ]


# Global console instance and Questionary style initialized with default theme
_active_palette = get_theme_palette(DEFAULT_THEME_KEY)
CUSTOM_THEME = build_rich_theme(_active_palette)
console = Console(theme=CUSTOM_THEME)
QUESTIONARY_STYLE = build_questionary_style(_active_palette)


def apply_active_theme(name: str) -> None:
    """Synchronize global console and Questionary styling with a specified theme."""
    global _CURRENT_THEME_KEY, _active_palette, CUSTOM_THEME, console, QUESTIONARY_STYLE
    _CURRENT_THEME_KEY = name
    _active_palette = get_theme_palette(name)
    CUSTOM_THEME = build_rich_theme(_active_palette)
    # Update console theme mapping in place
    console._theme = CUSTOM_THEME
    new_style = build_questionary_style(_active_palette)
    if hasattr(QUESTIONARY_STYLE, "_style_rules"):
        QUESTIONARY_STYLE._style_rules = new_style._style_rules
    QUESTIONARY_STYLE = new_style

