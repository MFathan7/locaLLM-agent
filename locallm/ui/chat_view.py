from typing import Any, Generator, List, Optional
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from locallm.ui.theme import console, get_theme_palette


def render_chat_welcome_card(
    config: Any,
    model_name: str,
    features: Optional[List[str]] = None,
) -> None:
    """Display an interactive assistant session card with themed ASCII styling."""
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))
    features_str = ", ".join(features) if features else "Text Generation"
    active_ws = getattr(config, "active_workspace", "default")
    ctx_limit = getattr(config, "context_window", 8192)

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    grid.add_row(
        f"[{palette.primary}]◆ Model:[/] [white]{model_name}[/]",
        f"[{palette.accent}]★ Capabilities:[/] [{palette.success}]{features_str}[/]",
    )
    grid.add_row(
        f"[{palette.primary}]▸ Workspace:[/] [white]{active_ws}[/]",
        f"[{palette.accent}]▰ Context Limit:[/] [white]{ctx_limit:,} tokens[/]",
    )

    full = Table.grid(expand=True)
    full.add_column(justify="left")
    full.add_row(grid)
    full.add_row(f"[{palette.dim}]Shortcuts:[/] [white]Enter[/] [dim](send)[/] [dim]•[/] [white]Ctrl+J[/] [dim](newline)[/]")
    full.add_row(f"[{palette.dim}]Commands:[/] [{palette.primary}]/help, /stats, /model, /clear, /sessions, /back, /exit[/]")

    panel = Panel(
        full,
        title=f"[bold {palette.primary}]⟦{palette.icon} {palette.name} Interactive Assistant⟧[/]",
        box=palette.box_style,
        border_style=palette.border_style,
        padding=(0, 2),
    )
    console.print(panel)
    console.print()



def print_user_prompt(text: str) -> None:
    """Display user question line with themed ASCII glyph."""
    palette = get_theme_palette()
    console.print()
    console.print(f"[bold {palette.primary}]{palette.user_prefix}[/] [dim]›[/] [white]{text}[/]")


def get_bracket_top(model_name: Optional[str] = None) -> str:
    """Generate the top bracket header with active theme icon and model name."""
    palette = get_theme_palette()
    if not model_name:
        try:
            from locallm.config import load_config
            cfg = load_config()
            model_name = getattr(cfg, "model", "locaLLM")
        except Exception:
            model_name = "locaLLM"

    raw_width = console.width if console.width else 80
    term_width = max(50, min(raw_width - 2, 78))

    header_content = f"{palette.icon} locaLLM · {model_name}"
    plain_bracket = f"⟦{header_content}⟧"
    dashes_count = max(4, term_width - len(plain_bracket) - 4)

    return (
        f"[bold {palette.primary}]┌─[/] "
        f"[bold {palette.accent}]⟦[/][bold white]{palette.icon} locaLLM[/] [dim]·[/] [bold {palette.primary}]{model_name}[/][bold {palette.accent}]⟧[/] "
        f"[bold {palette.primary}]" + ("─" * dashes_count) + "┐[/]"
    )


def get_bracket_bottom(
    stats: Optional[dict] = None,
    context_limit: int = 8192,
) -> str:
    """Generate the bottom bracket footer with telemetry and speed stats."""
    palette = get_theme_palette()
    raw_width = console.width if console.width else 80
    term_width = max(50, min(raw_width - 2, 78))

    if stats:
        prompt_tok = stats.get("prompt_eval_count", 0)
        eval_tok = stats.get("eval_count", 0)
        total_tok = prompt_tok + eval_tok
        eval_dur_ns = stats.get("eval_duration", 0)
        tps = (eval_tok / (eval_dur_ns / 1e9)) if eval_dur_ns > 0 else 0.0
        latency_s = eval_dur_ns / 1e9 if eval_dur_ns > 0 else 0.0

        if total_tok > 0:
            limit = max(context_limit, total_tok)
            pct = (total_tok / limit * 100) if limit > 0 else 0.0
            pct_color = palette.success if pct < 70 else (palette.warning if pct < 90 else palette.danger)

            formatted_bracket = (
                f"[bold {palette.accent}]⟦[/]"
                f"[{palette.dim}]• Context:[/] [{palette.primary}]{total_tok:,}[/][{palette.dim}]/[/][white]{limit:,}[/] "
                f"([{pct_color}]{pct:.1f}%[{palette.dim}]) [dim]•[/] "
                f"[{palette.dim}]Speed:[/] [{palette.primary}]{tps:.1f}[/] [{palette.dim}]tok/s[/]"
            )
            plain_stats = f"• Context: {total_tok:,}/{limit:,} ({pct:.1f}%) • Speed: {tps:.1f} tok/s"

            if latency_s > 0:
                formatted_bracket += f" [dim]•[/] [{palette.dim}]Latency:[/] [{palette.primary}]{latency_s:.1f}s[/]"
                plain_stats += f" • Latency: {latency_s:.1f}s"

            formatted_bracket += f"[bold {palette.accent}]⟧[/]"
            plain_len = len(f"⟦{plain_stats}⟧")
            dashes_count = max(4, term_width - plain_len - 4)

            return (
                f"[bold {palette.primary}]└─[/] "
                f"{formatted_bracket} "
                f"[bold {palette.primary}]" + ("─" * dashes_count) + "┘[/]"
            )

    dashes_count = max(4, term_width - 2)
    return f"[bold {palette.primary}]└" + ("─" * dashes_count) + "┘[/]"


def render_response_stats(
    stats: Optional[dict],
    context_limit: int = 8192,
) -> None:
    """Print the closing bottom bracket with telemetry and speed stats."""
    if not stats:
        palette = get_theme_palette()
        raw_width = console.width if console.width else 80
        term_width = max(50, min(raw_width - 2, 78))
        dashes_count = max(4, term_width - 2)
        console.print(f"[bold {palette.primary}]└" + ("─" * dashes_count) + "┘[/]\n")
        return
    console.print(get_bracket_bottom(stats, context_limit=context_limit))
    console.print()


def print_assistant_response(
    text: str,
    stats: Optional[dict] = None,
    context_limit: int = 8192,
    model_name: Optional[str] = None,
) -> None:
    """Render a complete assistant response cleanly parsed as Markdown inside an open Bracket Frame."""
    console.print()
    console.print(get_bracket_top(model_name=model_name))
    console.print()
    console.print(Markdown(text.strip()))
    console.print()
    render_response_stats(stats, context_limit=context_limit)


def stream_assistant_response(
    token_generator: Generator[str, None, None],
    stats: Optional[dict] = None,
    context_limit: int = 8192,
    model_name: Optional[str] = None,
) -> str:
    """Stream assistant markdown response in real-time inside an open Bracket Frame."""
    from locallm.ui.spinner import thinking_spinner

    first_chunk: Optional[str] = None
    with thinking_spinner("locaLLM is thinking..."):
        try:
            first_chunk = next(token_generator)
        except (StopIteration, Exception):
            first_chunk = None

    if first_chunk is None:
        return ""

    accumulated_text = first_chunk
    console.print()
    console.print(get_bracket_top(model_name=model_name))
    console.print()

    try:
        with Live(Markdown(accumulated_text), console=console, refresh_per_second=12) as live:
            for chunk in token_generator:
                accumulated_text += chunk
                live.update(Markdown(accumulated_text))
    except Exception:
        console.print(Markdown(accumulated_text))

    console.print()
    render_response_stats(stats, context_limit=context_limit)
    return accumulated_text


def print_system_info(message: str) -> None:
    """Print system or command feedback with themed glyph."""
    palette = get_theme_palette()
    console.print(f"[bold {palette.accent}]{palette.icon}[/] [{palette.dim}]{message}[/]")


def print_help_commands() -> None:
    """Display slash command reference table."""
    palette = get_theme_palette()
    commands = [
        ("/help", "Show this slash command cheat-sheet"),
        ("/model", "Switch active model on the fly"),
        ("/system", "View or modify current system instructions"),
        ("/clear", "Reset current conversation memory"),
        ("/new", "Start a fresh chat session"),
        ("/sessions", "List and resume saved workspace chat sessions"),
        ("/delete", "Delete active, specific, or all saved chat sessions"),
        ("/stats", "Display Ollama latency and context usage"),
        ("/back", "Return to main interactive menu"),
        ("/exit", "Terminate locaLLM session"),
    ]
    lines = [f"[bold {palette.primary}]{cmd:<12}[/] [{palette.dim}]-[/] [white]{desc}[/]" for cmd, desc in commands]
    content = "\n".join(lines)
    console.print(Panel(
        content,
        title=f"[bold {palette.primary}]⟦{palette.icon} Available Slash Commands⟧[/]",
        box=palette.box_style,
        border_style=palette.border_style,
    ))



def print_conversational_cli_help() -> None:
    """Display rich, conversational CLI guide from the locaLLM assistant."""
    from rich.table import Table

    intro_text = (
        "[bold white]Hello! I'm locaLLM, your autonomous local AI platform.[/]\n"
        "[#aaaaaa]I am designed to run large language models locally at peak speed,\n"
        "featuring isolated project sandboxes, local tool automation (files, shell, web), and 24/7 bot runners.\n"
        "Launch [/][bold cyan]locaLLM[/][#aaaaaa] without arguments to open the interactive TUI dashboard, or use the commands below:[/]\n"
    )

    table = Table(
        box=None,
        padding=(0, 2),
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Command", style="bold cyan", width=22)
    table.add_column("Description", style="white")

    # Group 1: Interactive & Workspaces
    table.add_row("[bold #00ff87]--- Interactive & Workspaces ---[/]", "")
    table.add_row("locallm chat", "Start interactive conversation session with silent tool execution")
    table.add_row("locallm agent", "Run autonomous ReAct agent loop for multi-step tasks (files, shell, web)")
    table.add_row("locallm workspace", "Manage isolated zero-bleed workspaces, knowledge docs, and skills")

    # Group 2: Integrations & Channels
    table.add_row("", "")
    table.add_row("[bold #00ff87]--- Integrations & Bot Runners ---[/]", "")
    table.add_row("locallm telegram", "Run 24/7 Telegram bot with user ID whitelist and multi-user memory")
    table.add_row("locallm whatsapp", "Run WhatsApp bot with terminal QR pairing and phone whitelist")

    # Group 3: Control & Ops
    table.add_row("", "")
    table.add_row("[bold #00ff87]--- Control & Utilities ---[/]", "")
    table.add_row("locallm run \"<prompt>\"", "Execute a single prompt turn and stream results to terminal")
    table.add_row("locallm models", "Inspect installed models, sizes, GPU VRAM fit check, and pull models")
    table.add_row("locallm platform", "Manage custom OpenAI-compatible platforms (list, add, remove, use)")
    table.add_row("locallm plugin", "Manage modular customizable plugins, database connectors, and tools")
    table.add_row("locallm service", "Manage background server daemon lifecycle (start, stop, status)")
    table.add_row("locallm start [target]", "Start Ollama background daemon (default: ollama)")
    table.add_row("locallm stop [target]", "Stop local service processes and release GPU VRAM")
    table.add_row("locallm status", "Inspect backend connection, GPU VRAM, and active model features")
    table.add_row("locallm config", "Configure global inference settings (backend, temperature, context)")

    examples_text = (
        "\n[bold cyan]Quickstart Examples:[/]\n"
        "  [#00d7ff]locaLLM[/]                                       [#888888]# Open Interactive TUI Dashboard[/]\n"
        "  [#00d7ff]locaLLM chat --model gemma4:12b[/]               [#888888]# Interactive chat with specific model[/]\n"
        "  [#00d7ff]locaLLM run \"Summarize README.md\"[/]             [#888888]# Single-shot prompt execution[/]\n"
        "  [#00d7ff]locaLLM workspace use project-ai[/]              [#888888]# Switch active workspace[/]\n"
        "  [#00d7ff]locaLLM <command> --help[/]                       [#888888]# Detailed help for specific subcommand[/]"
    )

    full_content = f"{intro_text}\n"
    console.print(Panel(
        table,
        title="[bold cyan]✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ   ɢ ᴜ ɪ ᴅ ᴇ  ✦[/]",
        subtitle="[#aaaaaa]Developer-First Autonomous Local AI Platform[/]",
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print(examples_text)
    console.print()


import random

FAREWELL_QUOTES = [
    ("Catch ya later!", "locaLLM signing out. VRAM is back in your hands."),
    ("Peace out!", "Weights dumped, GPU is chilling now."),
    ("locaLLM dipping out!", "Memory cleared. Go build something sick."),
    ("Aight, I'm outta here!", "VRAM released. Hit me up whenever you need me."),
    ("See ya around, boss!", "VRAM unloaded cleanly. Catch you on the flip side."),
    ("Signing off for now!", "Everything wrapped up clean. Happy hacking!"),
    ("That's a wrap!", "Models flushed from memory. Stay awesome!"),
    ("locaLLM out!", "All done here. Your GPU can take a breather now."),
    ("Later, legend!", "VRAM's all cleared up. Catch you in the next run."),
    ("Take it easy!", "Clean shutdown complete. Don't forget to push your code!"),
]



def render_application_farewell(unloaded_count: int = 0) -> None:
    """Display short, dynamic conversational persona farewell when exiting locaLLM."""
    title, subtitle = random.choice(FAREWELL_QUOTES)
    console.print(f"\n[bold cyan]{title}[/] [dim white]{subtitle}[/]\n")


