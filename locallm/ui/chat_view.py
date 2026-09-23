import time
from typing import Any, Generator, List, Optional, Tuple
from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from locallm.ui.theme import console, get_theme_palette

SPINNER_FRAMES = ["▘", "▀", "▝", "▐", "▗", "▄", "▖", "▌"]


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

    raw_width = console.width if isinstance(getattr(console, "width", None), int) else 80
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
    raw_width = console.width if isinstance(getattr(console, "width", None), int) else 80
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
        raw_width = console.width if isinstance(getattr(console, "width", None), int) else 80
        term_width = max(50, min(raw_width - 2, 78))
        dashes_count = max(4, term_width - 2)
        console.print(f"[bold {palette.primary}]└" + ("─" * dashes_count) + "┘[/]\n")
        return
    console.print(get_bracket_bottom(stats, context_limit=context_limit))
    console.print()


def extract_thought_process(text: str) -> Tuple[Optional[str], str]:
    """Separate reasoning thoughts enclosed in <think>...</think> from main content."""
    if "<think>" not in text:
        return None, text

    if "</think>" in text:
        parts = text.split("</think>", 1)
        thought = parts[0].split("<think>", 1)[1].strip()
        remaining = parts[1].strip()
        return (thought if thought else None), remaining

    parts = text.split("<think>", 1)
    thought = parts[1].strip()
    return (thought if thought else None), ""


def print_assistant_response(
    text: str,
    stats: Optional[dict] = None,
    context_limit: int = 8192,
    model_name: Optional[str] = None,
) -> None:
    """Render a complete assistant response cleanly parsed as Markdown inside an open Bracket Frame."""
    palette = get_theme_palette()
    console.print()
    console.print(get_bracket_top(model_name=model_name))
    console.print()

    thought_content, main_content = extract_thought_process(text)
    if thought_content:
        thought_panel = Panel(
            Text(thought_content, style=f"italic {palette.dim}"),
            title=f"[{palette.accent}]💭 Thought Process[/]",
            box=palette.box_style,
            border_style=palette.border_style,
            padding=(0, 1),
        )
        console.print(thought_panel)
        console.print()

    if main_content.strip():
        console.print(Markdown(main_content.strip()))
    elif not thought_content:
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
    from locallm.core.hardware import get_gpu_info

    palette = get_theme_palette()

    first_chunk: Optional[str] = None
    with thinking_spinner("locaLLM is thinking..."):
        try:
            first_chunk = next(token_generator)
        except (StopIteration, Exception):
            first_chunk = None

    if first_chunk is None:
        return ""

    raw_buffer = first_chunk
    stream_start_time = time.time()
    total_tokens = 1

    # Check VRAM allocation
    gpu = get_gpu_info()
    if gpu and gpu.total_vram_mb > 0:
        vram_str = f"{gpu.used_vram_mb / 1024.0:.1f}/{gpu.total_vram_mb / 1024.0:.1f} GB"
    else:
        vram_str = "CPU"

    console.print()
    console.print(get_bracket_top(model_name=model_name))
    console.print()

    thought_start_time = stream_start_time if "<think>" in raw_buffer else None
    thought_elapsed = 0.0

    def _parse_buffer(buf: str) -> Tuple[str, str, bool, bool]:
        """Parse raw buffer into (thought_text, main_text, in_thinking, thought_finished)."""
        if "<think>" in buf:
            if "</think>" in buf:
                parts = buf.split("</think>", 1)
                t = parts[0].split("<think>", 1)[1]
                m = parts[1]
                return t, m, False, True
            else:
                t = buf.split("<think>", 1)[1]
                return t, "", True, False
        else:
            return "", buf, False, False

    def _render_current_state(
        buf: str,
        show_speedometer: bool = True,
        show_cursor: bool = True,
    ) -> Group:
        nonlocal thought_start_time, thought_elapsed
        t_text, m_text, in_think, think_done = _parse_buffer(buf)

        if in_think and thought_start_time is None:
            thought_start_time = time.time()

        if in_think and thought_start_time is not None:
            thought_elapsed = time.time() - thought_start_time
        elif think_done and thought_start_time is not None and thought_elapsed == 0.0:
            thought_elapsed = time.time() - thought_start_time

        cursor_char = "▌"
        items: List[Any] = []
        if t_text.strip():
            if in_think:
                thought_title = f"[italic {palette.accent}]💭 Thought Process[/] [{palette.dim}]({thought_elapsed:.1f}s)[/]"
                display_t = t_text.strip() + (f" {cursor_char}" if show_cursor else "")
                items.append(Panel(
                    Text(display_t, style=f"italic {palette.dim}"),
                    title=thought_title,
                    box=palette.box_style,
                    border_style=palette.border_style,
                    padding=(0, 1),
                ))
                items.append(Text(""))
            elif think_done:
                items.append(Text.from_markup(f"[{palette.accent}]✔ Thought for {thought_elapsed:.1f}s[/]\n"))

        if m_text.strip():
            display_m = m_text.strip() + (f" {cursor_char}" if show_cursor else "")
            if display_m.count("```") % 2 == 1:
                display_m += "\n```"
            items.append(Markdown(display_m))

        if show_speedometer:
            now = time.time()
            elapsed = max(0.001, now - stream_start_time)
            tok_per_sec = total_tokens / elapsed
            spinner_glyph = SPINNER_FRAMES[total_tokens % len(SPINNER_FRAMES)]
            speedo = (
                f"[{palette.dim}]{spinner_glyph} Emitting:[/] "
                f"[bold {palette.primary}]{total_tokens}[/] [{palette.dim}]tokens[/] [dim]•[/] "
                f"[bold {palette.success}]{tok_per_sec:.1f}[/] [{palette.dim}]tok/s[/] [dim]•[/] "
                f"[bold white]{elapsed:.1f}s[/] [dim]• VRAM:[/] [{palette.primary}]{vram_str}[/]"
            )
            items.append(Text(""))
            items.append(Text.from_markup(speedo))

        if not items:
            items.append(Text(cursor_char if show_cursor else ""))

        return Group(*items)

    try:
        with Live(
            _render_current_state(raw_buffer, show_speedometer=True, show_cursor=True),
            console=console,
            refresh_per_second=24,
        ) as live:
            for chunk in token_generator:
                if len(chunk) > 6 and " " in chunk:
                    words = chunk.split(" ")
                    for idx, word in enumerate(words):
                        sub = word + (" " if idx < len(words) - 1 else "")
                        raw_buffer += sub
                        total_tokens += 1
                        live.update(_render_current_state(raw_buffer, show_speedometer=True, show_cursor=True))
                        time.sleep(0.012)
                else:
                    raw_buffer += chunk
                    total_tokens += 1
                    live.update(_render_current_state(raw_buffer, show_speedometer=True, show_cursor=True))

            # Final clean state without speedometer or cursor so terminal settles cleanly
            live.update(_render_current_state(raw_buffer, show_speedometer=False, show_cursor=False))
    except Exception:
        thought_content, main_content = extract_thought_process(raw_buffer)
        if main_content.strip():
            console.print(Markdown(main_content.strip()))
        else:
            console.print(Markdown(raw_buffer))

    console.print()
    render_response_stats(stats, context_limit=context_limit)

    _, clean_main, _, _ = _parse_buffer(raw_buffer)
    return clean_main.strip() if clean_main.strip() else raw_buffer.strip()



def print_system_info(message: str) -> None:
    """Print system or command feedback with themed glyph."""
    palette = get_theme_palette()
    console.print(f"[bold {palette.accent}]{palette.icon}[/] [{palette.dim}]{message}[/]")


def print_help_commands() -> None:
    """Display slash command reference table."""
    palette = get_theme_palette()
    commands = [
        ("/help", "Show this slash command cheat-sheet"),
        ("/top", "Open real-time system & VRAM monitor HUD"),
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



def print_conversational_cli_help(theme: Optional[str] = None) -> None:
    """Display rich, conversational CLI guide from the locaLLM assistant."""
    from rich.table import Table
    if theme is None:
        try:
            from locallm.config import load_config
            theme = load_config().ui_theme
        except Exception:
            theme = "cyber_neon"
    palette = get_theme_palette(theme)

    intro_text = (
        "[bold white]Hello! I'm locaLLM, your autonomous local AI platform.[/]\n"
        "[#aaaaaa]I am designed to run large language models locally at peak speed,\n"
        "featuring isolated project sandboxes, local tool automation (files, shell, web), and 24/7 bot runners.\n"
        f"Launch [/][bold {palette.primary}]locaLLM[/][#aaaaaa] without arguments to open the interactive main menu, or use the commands below:[/]\n"
    )

    table = Table(
        box=None,
        padding=(0, 2),
        show_header=True,
        header_style=f"bold {palette.primary}",
    )
    table.add_column("Command", style=f"bold {palette.primary}", width=22)
    table.add_column("Description", style="white")

    # Group 1: Interactive & Workspaces
    table.add_row(f"[bold {palette.success}]--- Interactive & Workspaces ---[/]", "")
    table.add_row("locallm chat", "Start interactive conversation session with silent tool execution")
    table.add_row("locallm agent", "Run autonomous ReAct agent loop for multi-step tasks (files, shell, web)")
    table.add_row("locallm workspace", "Manage isolated zero-bleed workspaces, knowledge docs, and skills")

    # Group 2: Integrations & Channels
    table.add_row("", "")
    table.add_row(f"[bold {palette.success}]--- Integrations & Bot Runners ---[/]", "")
    table.add_row("locallm telegram", "Run 24/7 Telegram bot with user ID whitelist and multi-user memory")
    table.add_row("locallm whatsapp", "Run WhatsApp bot with terminal QR pairing and phone whitelist")

    # Group 3: Control & Ops
    table.add_row("", "")
    table.add_row(f"[bold {palette.success}]--- Control & Utilities ---[/]", "")
    table.add_row("locallm run \"<prompt>\"", "Execute a single prompt turn and stream results to terminal")
    table.add_row("locallm top", "Launch live real-time VRAM & hardware telemetry monitor HUD")
    table.add_row("locallm models", "Inspect installed models, sizes, GPU VRAM fit check, and pull models")
    table.add_row("locallm platform", "Manage custom OpenAI-compatible platforms (list, add, remove, use)")
    table.add_row("locallm plugin", "Manage modular customizable plugins, database connectors, and tools")
    table.add_row("locallm service", "Manage background server daemon lifecycle (start, stop, status)")
    table.add_row("locallm start [target]", "Start Ollama background daemon (default: ollama)")
    table.add_row("locallm stop [target]", "Stop local service processes and release GPU VRAM")
    table.add_row("locallm status", "Inspect backend connection, GPU VRAM, and active model features")
    table.add_row("locallm config", "Configure global inference settings (backend, temperature, context)")

    examples_text = (
        f"\n[bold {palette.primary}]Quickstart Examples:[/]\n"
        f"  [{palette.accent}]locaLLM[/]                                       [#888888]# Open Interactive Main Menu[/]\n"
        f"  [{palette.accent}]locaLLM chat --model gemma4:12b[/]               [#888888]# Interactive chat with specific model[/]\n"
        f"  [{palette.accent}]locaLLM top[/]                                   [#888888]# Open Live System Monitor HUD[/]\n"
        f"  [{palette.accent}]locaLLM run \"Summarize README.md\"[/]             [#888888]# Single-shot prompt execution[/]\n"
        f"  [{palette.accent}]locaLLM workspace use project-ai[/]              [#888888]# Switch active workspace[/]\n"
        f"  [{palette.accent}]locaLLM <command> --help[/]                       [#888888]# Detailed help for specific subcommand[/]"
    )

    console.print(Panel(
        table,
        title=f"[bold {palette.primary}]✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ   ɢ ᴜ ɪ ᴅ ᴇ  ✦[/]",
        subtitle="[#aaaaaa]Developer-First Autonomous Local AI Platform[/]",
        border_style=palette.border_style,
        box=palette.box_style,
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


def render_application_farewell(unloaded_count: int = 0, theme: Optional[str] = None) -> None:
    """Display short, dynamic conversational persona farewell when exiting locaLLM."""
    if theme is None:
        try:
            from locallm.config import load_config
            theme = load_config().ui_theme
        except Exception:
            theme = "cyber_neon"
    palette = get_theme_palette(theme)
    title, subtitle = random.choice(FAREWELL_QUOTES)
    console.print(f"\n[bold {palette.primary}]{title}[/] [dim white]{subtitle}[/]\n")


