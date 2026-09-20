"""Chat streaming and conversation renderer."""

from typing import Generator, Optional
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from locallm.ui.theme import console


def print_user_prompt(text: str) -> None:
    """Display user question panel."""
    console.print()
    console.print(f"[bold cyan]You >[/] [white]{text}[/]")


def render_response_stats(
    stats: Optional[dict],
    context_limit: int = 8192,
) -> None:
    """Print a clean, non-purple context usage and speed footer below AI responses."""
    if not stats:
        return
    prompt_tok = stats.get("prompt_eval_count", 0)
    eval_tok = stats.get("eval_count", 0)
    total_tok = prompt_tok + eval_tok
    eval_dur_ns = stats.get("eval_duration", 0)
    tps = (eval_tok / (eval_dur_ns / 1e9)) if eval_dur_ns > 0 else 0.0

    if total_tok > 0:
        limit = max(context_limit, total_tok)
        pct = (total_tok / limit * 100) if limit > 0 else 0.0
        pct_color = "#00ff87" if pct < 70 else ("#ffff00" if pct < 90 else "#ff5555")
        console.print(
            f"[#aaaaaa]  • Context:[/] [#00d7ff]{total_tok:,}[/][#aaaaaa]/[/][#ffffff]{limit:,}[/] [#aaaaaa]tokens "
            f"([{pct_color}]{pct:.1f}%[#aaaaaa]) • Speed:[/] [#00d7ff]{tps:.1f}[/] [#aaaaaa]tok/s[/]\n"
        )


def print_assistant_response(
    text: str,
    stats: Optional[dict] = None,
    context_limit: int = 8192,
) -> None:
    """Render a complete assistant response cleanly parsed as Markdown."""
    console.print("[bold green]locaLLM >[/] ")
    console.print(Markdown(text.strip()))
    console.print()
    if stats:
        render_response_stats(stats, context_limit=context_limit)


def stream_assistant_response(
    token_generator: Generator[str, None, None],
    stats: Optional[dict] = None,
    context_limit: int = 8192,
) -> str:
    """Stream assistant markdown response in real-time with thinking spinner.

    Automatically parses bold, italics, lists, and code blocks live on terminal.

    Returns:
        str: Accumulated complete response text.
    """
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
    console.print("[bold green]locaLLM >[/] ")

    try:
        with Live(Markdown(accumulated_text), console=console, refresh_per_second=12) as live:
            for chunk in token_generator:
                accumulated_text += chunk
                live.update(Markdown(accumulated_text))
    except Exception:
        # Resilient fallback if terminal interrupt occurs
        console.print(Markdown(accumulated_text))

    console.print()
    if stats:
        render_response_stats(stats, context_limit=context_limit)
    return accumulated_text


def print_system_info(message: str) -> None:
    """Print system or command feedback."""
    console.print(f"[#aaaaaa][*] {message}[/]")


def print_help_commands() -> None:
    """Display slash command reference table."""
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
    lines = [f"[bold cyan]{cmd:<12}[/] [#888888]-[/] [#cccccc]{desc}[/]" for cmd, desc in commands]
    content = "\n".join(lines)
    console.print(Panel(content, title="[bold cyan]Available Slash Commands[/]", border_style="cyan"))


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


