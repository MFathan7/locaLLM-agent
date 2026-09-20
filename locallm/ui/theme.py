import sys
from questionary import Style
from rich.console import Console
from rich.theme import Theme

# Ensure UTF-8 console output encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Rich terminal color scheme
CUSTOM_THEME = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "danger": "bold red",
        "success": "bold green",
        "highlight": "bold magenta",
        "dimmed": "dim white",
        "model": "bold cyan",
        "vram_ok": "bold green",
        "vram_warn": "bold yellow",
        "vram_bad": "bold red",
    }
)

console = Console(theme=CUSTOM_THEME)

# Questionary interactive prompt styling (clean, sleek, no emojis)
QUESTIONARY_STYLE = Style(
    [
        ("qmark", "fg:#00d7ff bold"),
        ("question", "bold fg:#ffffff"),
        ("answer", "fg:#00ff87 bold"),
        ("pointer", "fg:#00d7ff bold"),
        ("highlighted", "fg:#00d7ff bold"),
        ("selected", "fg:#00ff87"),
        ("separator", "fg:#555555"),
        ("instruction", "fg:#888888 italic"),
        ("text", "fg:#dddddd"),
        ("disabled", "fg:#666666 italic"),
    ]
)
