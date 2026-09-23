"""TCSS theme generator and color mapping for locaLLM Textual TUI."""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from locallm.ui.theme import THEME_DEFINITIONS, ThemePalette, get_theme_palette


@dataclass(frozen=True)
class TuiThemeSpec:
    """TUI-specific styling tokens mapped from core ThemePalette."""

    key: str
    name: str
    icon: str
    badge: str
    bg_screen: str
    bg_surface: str
    bg_card: str
    border: str
    primary: str
    accent: str
    success: str
    warning: str
    danger: str
    dim: str
    text: str


TUI_THEME_SPECS: Dict[str, TuiThemeSpec] = {
    "cyber_neon": TuiThemeSpec(
        key="cyber_neon",
        name="Cyber Neon",
        icon="⚡",
        badge="⟦⚡ CYBER⟧",
        bg_screen="#080b11",
        bg_surface="#0f1523",
        bg_card="#151e32",
        border="#00f0ff",
        primary="#00f0ff",
        accent="#ff007f",
        success="#00ff66",
        warning="#ffe600",
        danger="#ff3366",
        dim="#707d9b",
        text="#e6edf3",
    ),
    "tokyo_night": TuiThemeSpec(
        key="tokyo_night",
        name="Tokyo Night",
        icon="◈",
        badge="⟦◈ TOKYO⟧",
        bg_screen="#16161e",
        bg_surface="#1a1b26",
        bg_card="#24283b",
        border="#7aa2f7",
        primary="#7aa2f7",
        accent="#bb9af7",
        success="#73daca",
        warning="#e0af68",
        danger="#f7768e",
        dim="#565f89",
        text="#c0caf5",
    ),
    "monokai": TuiThemeSpec(
        key="monokai",
        name="Monokai",
        icon="★",
        badge="⟦★ RETRO⟧",
        bg_screen="#1b1c18",
        bg_surface="#272822",
        bg_card="#383730",
        border="#ffd866",
        primary="#ffd866",
        accent="#ff6188",
        success="#a9dc76",
        warning="#fc9867",
        danger="#ff4060",
        dim="#727072",
        text="#f8f8f2",
    ),
    "matrix": TuiThemeSpec(
        key="matrix",
        name="Matrix",
        icon="λ",
        badge="⟦λ MATRIX⟧",
        bg_screen="#040804",
        bg_surface="#081408",
        bg_card="#0f220f",
        border="#39ff14",
        primary="#39ff14",
        accent="#ffffff",
        success="#00ff41",
        warning="#ffb000",
        danger="#ff0033",
        dim="#1b5e20",
        text="#e0ffe0",
    ),
    "nordic_frost": TuiThemeSpec(
        key="nordic_frost",
        name="Nordic Frost",
        icon="❄",
        badge="⟦❄ FROST⟧",
        bg_screen="#1e222a",
        bg_surface="#2e3440",
        bg_card="#3b4252",
        border="#88c0d0",
        primary="#88c0d0",
        accent="#81a1c1",
        success="#a3be8c",
        warning="#ebcb8b",
        danger="#bf616a",
        dim="#4c566a",
        text="#eceff4",
    ),
}


def get_tui_theme(name: str = "cyber_neon") -> TuiThemeSpec:
    """Retrieve TuiThemeSpec for a theme key with fallback to cyber_neon."""
    key = name.strip().lower() if name else "cyber_neon"
    return TUI_THEME_SPECS.get(key, TUI_THEME_SPECS["cyber_neon"])


def list_tui_themes() -> List[Tuple[str, str, str]]:
    """Return list of (key, name, badge) for all available themes."""
    return [(spec.key, spec.name, spec.badge) for spec in TUI_THEME_SPECS.values()]


def build_app_tcss() -> str:
    """Generate master TCSS stylesheet containing base layout rules and scoped theme classes."""
    base_css = """
/* Base Master Layout */
Screen {
    layout: vertical;
    overflow: hidden;
}

#header-container {
    height: 3;
    dock: top;
    layout: horizontal;
    padding: 0 1;
    border-bottom: solid;
}

#header-title {
    width: 1fr;
    content-align: left middle;
    text-style: bold;
}

#header-status {
    width: auto;
    content-align: right middle;
}

#main-app-tabs {
    height: 1fr;
    width: 100%;
}

#main-app-tabs ContentSwitcher {
    height: 1fr;
    width: 100%;
}

TabPane {
    height: 1fr;
    width: 100%;
    padding: 0;
}

ModelsView, WorkspacesView, IntegrationsView, PluginsView, ServicesView, SettingsView {
    height: 1fr;
    width: 100%;
}

#main-body {
    height: 1fr;
    layout: horizontal;
}

#left-pane {
    width: 68%;
    height: 100%;
    layout: vertical;
}

#right-pane {
    width: 32%;
    height: 100%;
    layout: vertical;
    overflow-y: auto;
    border-left: solid;
}

#chat-scroll {
    height: 1fr;
    overflow-y: auto;
    padding: 0 1;
}

#chat-messages-container {
    height: auto;
    layout: vertical;
}

#prompt-container {
    height: auto;
    min-height: 4;
    max-height: 8;
    dock: bottom;
    padding: 0 1 1 1;
    layout: horizontal;
    border-top: solid;
}

#prompt-input {
    width: 1fr;
    border: tall;
}

#send-button {
    width: auto;
    min-width: 10;
    margin-left: 1;
    height: 3;
    border: tall;
}

#footer-container {
    height: 1;
    dock: bottom;
    content-align: center middle;
    padding: 0 1;
}

/* Chat Messages */
.chat-msg {
    margin: 1 0;
    padding: 0 1;
    border-left: heavy;
    height: auto;
}

.chat-msg-user {
    border-left: double;
}

.chat-msg-assistant {
    border-left: heavy;
}

.chat-msg-header {
    text-style: bold;
    margin-bottom: 0;
}

.chat-msg-body {
    height: auto;
}

/* Tool Execution Cards */
.tool-card {
    margin: 1 0;
    padding: 0 1;
    border: round;
    height: auto;
}

.tool-card-running {
    border-subtitle-align: right;
}

.tool-card-completed {
    border-subtitle-align: right;
}

.tool-card-header {
    text-style: bold;
}

.tool-card-details {
    height: auto;
    padding: 0 1;
    margin-top: 1;
    border-top: dashed;
}

/* Sidebar Tabbed Layout */
#sidebar-tabs {
    height: 100%;
}

.tab-pane-content {
    padding: 1;
    height: 100%;
    overflow-y: auto;
}

.stat-box {
    margin-bottom: 1;
    padding: 1;
    border: round;
    height: auto;
}

.stat-title {
    text-style: bold;
    margin-bottom: 0;
}

.stat-row {
    margin: 0 0;
}

ProgressBar {
    margin-top: 0;
    margin-bottom: 1;
}

/* Theme Selector Buttons */
.theme-select-btn {
    width: 100%;
    margin-bottom: 1;
    border: round;
}

/* Modal Dialog */
#theme-modal-dialog {
    padding: 1 2;
    border: double;
    width: 60;
    height: auto;
    align: center middle;
}
"""
    # Generate dynamic class rules for each theme
    theme_rules = []
    for spec in TUI_THEME_SPECS.values():
        rule = f"""
/* Theme: {spec.name} ({spec.key}) */
Screen.theme-{spec.key} {{
    background: {spec.bg_screen};
    color: {spec.text};
}}

Screen.theme-{spec.key} #header-container {{
    background: {spec.bg_surface};
    border-bottom: solid {spec.border};
    color: {spec.primary};
}}

Screen.theme-{spec.key} #header-title {{
    color: {spec.primary};
}}

Screen.theme-{spec.key} #header-status {{
    color: {spec.accent};
}}

Screen.theme-{spec.key} #right-pane {{
    background: {spec.bg_surface};
    border-left: solid {spec.dim};
}}

Screen.theme-{spec.key} #chat-scroll {{
    background: {spec.bg_screen};
}}

Screen.theme-{spec.key} #prompt-container {{
    background: {spec.bg_surface};
    border-top: solid {spec.dim};
}}

Screen.theme-{spec.key} #prompt-input {{
    background: {spec.bg_card};
    border: tall {spec.border};
    color: {spec.text};
}}

Screen.theme-{spec.key} #prompt-input:focus {{
    border: tall {spec.accent};
}}

Screen.theme-{spec.key} #send-button {{
    background: {spec.primary};
    color: {spec.bg_screen};
    border: tall {spec.border};
    text-style: bold;
}}

Screen.theme-{spec.key} #send-button:hover {{
    background: {spec.accent};
}}

Screen.theme-{spec.key} #footer-container {{
    background: {spec.bg_surface};
    color: {spec.dim};
}}

Screen.theme-{spec.key} .chat-msg-user {{
    background: {spec.bg_card};
    border-left: double {spec.accent};
}}

Screen.theme-{spec.key} .chat-msg-user .chat-msg-header {{
    color: {spec.accent};
}}

Screen.theme-{spec.key} .chat-msg-assistant {{
    background: {spec.bg_surface};
    border-left: heavy {spec.primary};
}}

Screen.theme-{spec.key} .chat-msg-assistant .chat-msg-header {{
    color: {spec.primary};
}}

Screen.theme-{spec.key} .tool-card {{
    background: {spec.bg_card};
    border: round {spec.dim};
}}

Screen.theme-{spec.key} .tool-card-running {{
    border: round {spec.warning};
}}

Screen.theme-{spec.key} .tool-card-completed {{
    border: round {spec.success};
}}

Screen.theme-{spec.key} .tool-card-failed {{
    border: round {spec.danger};
}}

Screen.theme-{spec.key} .tool-card-header {{
    color: {spec.primary};
}}

Screen.theme-{spec.key} .stat-box {{
    background: {spec.bg_card};
    border: round {spec.dim};
}}

Screen.theme-{spec.key} .stat-title {{
    color: {spec.primary};
}}

Screen.theme-{spec.key} TabbedContent {{
    background: {spec.bg_surface};
}}

Screen.theme-{spec.key} ContentTab {{
    color: {spec.dim};
}}

Screen.theme-{spec.key} ContentTab.-active {{
    color: {spec.primary};
    text-style: bold;
}}

Screen.theme-{spec.key} ProgressBar > .bar--bar {{
    color: {spec.primary};
    background: {spec.dim};
}}

Screen.theme-{spec.key} ProgressBar > .bar--complete {{
    color: {spec.success};
}}

Screen.theme-{spec.key} .theme-select-btn {{
    background: {spec.bg_card};
    border: round {spec.dim};
    color: {spec.text};
}}

Screen.theme-{spec.key} .theme-select-btn:hover {{
    background: {spec.bg_surface};
    border: round {spec.primary};
    color: {spec.primary};
}}

Screen.theme-{spec.key} .theme-select-btn-active {{
    background: {spec.bg_surface};
    border: round {spec.primary};
    color: {spec.primary};
    text-style: bold;
}}
"""
        theme_rules.append(rule)

    return base_css + "\n".join(theme_rules)
