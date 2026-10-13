"""Terminal TUI renderer for multi-agent team coordination in CLI."""

from typing import Any, Callable, Optional
from rich.panel import Panel
from locallm.core.orchestrator.supervisor import SupervisorOrchestrator
from locallm.ui.spinner import AssistantSpinner
from locallm.ui.theme import console, get_theme_palette


def create_multi_agent_event_callback(
    spinner: AssistantSpinner,
    console_instance: Optional[Any] = None,
) -> Callable[[str, str, str], None]:
    """Create a unified telemetry event handler that displays live progress and milestones."""
    c = console_instance or console

    def _on_event(agent: str, event_type: str, message: str) -> None:
        if agent == "Supervisor":
            if event_type == "start":
                spinner.print_task("[bold #00d7ff]✦ [Supervisor][/] Initializing mission orchestration...")
                spinner.update("Supervisor is analyzing mission objective...", style="bold #00d7ff")
            elif event_type == "team":
                spinner.print_task(f"[bold #00d7ff]✦ [Supervisor][/] [dim]{message}[/]")
            elif event_type == "planning":
                spinner.print_task(f"[bold #00d7ff]✦ [Supervisor][/] [bold white]{message}[/]")
                spinner.update("Supervisor is reasoning & planning delegation...", style="bold #00d7ff")
            elif event_type == "delegate":
                spinner.print_task(f"[bold cyan]↳ [Supervisor][/] [bold white]{message}[/]")
                spinner.update(f"Supervisor: Delegated to specialist...", style="bold cyan")
            elif event_type == "subtask_done":
                spinner.print_task(f"[bold #00d7ff]✦ [Supervisor][/] [dim]Received update:[/] {message}")
                spinner.update("Supervisor is reviewing updated blackboard...", style="bold #00d7ff")
            elif event_type == "complete":
                spinner.print_task("[bold green]✔ [Supervisor][/] [bold white]Mission goal achieved.[/]")
            elif event_type == "error":
                spinner.print_task(f"[bold red]✖ [Supervisor][/] {message}")

        elif agent == "ResearchAgent":
            if event_type == "start":
                spinner.print_task(f"  [bold yellow]🔍 [ResearchAgent][/] [dim]{message}[/]")
            elif event_type == "thinking":
                spinner.update("ResearchAgent is analyzing knowledge & sources...", style="bold yellow")
            elif event_type in ("tool", "tool_start"):
                spinner.print_task(f"  [bold yellow]🔍 [ResearchAgent][/] [dim]{message}[/]")
                spinner.update("ResearchAgent is fetching information...", style="bold yellow")
            elif event_type in ("tool_done", "tool_result"):
                spinner.print_task(f"  [bold yellow]✔ [ResearchAgent][/] [dim]{message}[/]")
            elif event_type == "done":
                spinner.print_task(f"  [bold yellow]✔ [ResearchAgent][/] [bold white]{message}[/]")
            elif event_type == "error":
                spinner.print_task(f"  [bold red]✖ [ResearchAgent][/] {message}")

        elif agent == "CoderAgent":
            if event_type == "start":
                spinner.print_task(f"  [bold green]⚡ [CoderAgent][/] [dim]{message}[/]")
            elif event_type == "thinking":
                spinner.update("CoderAgent is engineering code changes...", style="bold green")
            elif event_type in ("tool", "tool_start"):
                spinner.print_task(f"  [bold green]⚡ [CoderAgent][/] [dim]{message}[/]")
                spinner.update("CoderAgent is applying code edits...", style="bold green")
            elif event_type in ("tool_done", "tool_result"):
                spinner.print_task(f"  [bold green]✔ [CoderAgent][/] [dim]{message}[/]")
            elif event_type == "done":
                spinner.print_task(f"  [bold green]✔ [CoderAgent][/] [bold white]{message}[/]")
            elif event_type == "error":
                spinner.print_task(f"  [bold red]✖ [CoderAgent][/] {message}")

        elif agent == "AuditorAgent":
            if event_type == "start":
                spinner.print_task(f"  [bold magenta]🛡 [AuditorAgent][/] [dim]{message}[/]")
            elif event_type == "thinking":
                spinner.update("AuditorAgent is evaluating diagnostics & tests...", style="bold magenta")
            elif event_type in ("tool", "tool_start"):
                spinner.print_task(f"  [bold magenta]🛡 [AuditorAgent][/] [dim]{message}[/]")
                spinner.update("AuditorAgent is executing verification...", style="bold magenta")
            elif event_type in ("tool_done", "tool_result"):
                spinner.print_task(f"  [bold magenta]✔ [AuditorAgent][/] [dim]{message}[/]")
            elif event_type == "done":
                spinner.print_task(f"  [bold magenta]✔ [AuditorAgent][/] [bold white]{message}[/]")
            elif event_type == "error":
                spinner.print_task(f"  [bold red]✖ [AuditorAgent][/] {message}")

    return _on_event


def run_multi_agent_cli(task: str, config: Any, client: Any) -> None:
    """Execute a multi-agent team task with live formatted terminal telemetry."""
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))
    active_ws = getattr(config, "active_workspace", "default")

    orchestrator = SupervisorOrchestrator(config, client)

    # Header Card
    console.print(Panel(
        f"[bold white]{task}[/]\n\n"
        f"[#aaaaaa]Workspace:[/] [bold cyan]{active_ws}[/]\n"
        f"[#aaaaaa]Supervisor:[/] [bold #00d7ff]{orchestrator.supervisor_model}[/]\n"
        f"[#aaaaaa]Researcher:[/] [bold yellow]{orchestrator.researcher.model_name}[/]\n"
        f"[#aaaaaa]Coder Specialist:[/] [bold green]{orchestrator.coder.model_name}[/]\n"
        f"[#aaaaaa]Auditor Specialist:[/] [bold magenta]{orchestrator.auditor.model_name}[/]",
        title=f"[bold {palette.primary}]⟦ Multi-Agent Team Orchestration ⟧[/]",
        box=palette.box_style,
        border_style=palette.border_style,
    ))

    spinner = AssistantSpinner()
    spinner.start("Supervisor is assembling team and planning mission...", style="bold #00d7ff")
    callback = create_multi_agent_event_callback(spinner)

    try:
        blackboard = orchestrator.run(
            task=task,
            workspace_name=active_ws,
            on_event=callback,
        )
    finally:
        spinner.stop()

    # Final Result Card
    summary_lines = [blackboard.final_answer or "Mission concluded."]
    if blackboard.modified_files:
        summary_lines.append(f"\n[bold green]Files Touched:[/] {', '.join(blackboard.modified_files)}")
    if blackboard.test_results:
        summary_lines.append(f"[bold magenta]Verification Commands:[/] {len(blackboard.test_results)} executed")

    console.print(Panel(
        "\n".join(summary_lines),
        title=f"[bold green]⟦ Final Multi-Agent Mission Report ⟧[/]",
        box=palette.box_style,
        border_style="green",
    ))
