"""Interactive Assistant module with native function calling, tools, and stats."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import questionary
from rich.panel import Panel
from rich.table import Table
from locallm.config import LocaLLMConfig, save_config
from locallm.core.hardware import get_gpu_info
from locallm.core.memory import ConversationMemory
from locallm.core.ollama_client import OllamaClient
from locallm.core.tools import ASSISTANT_TOOLS, execute_tool
from locallm.core.workspace import (
    clear_all_workspace_sessions,
    delete_workspace_session,
    list_workspace_sessions,
    load_workspace_context,
    load_workspace_session,
    save_workspace_session,
)
from locallm.ui.chat_view import (
    print_assistant_response,
    print_help_commands,
    print_system_info,
    render_response_stats,
    stream_assistant_response,
)
from locallm.ui.spinner import thinking_spinner
from locallm.ui.theme import QUESTIONARY_STYLE, console


def run_assistant(config: LocaLLMConfig, client: Any) -> None:
    """Run interactive chat session with active backend and native tool automation."""
    if not client.is_connected():
        target_endpoint = (
            config.ollama_host
            if config.active_backend.lower() == "ollama"
            else getattr(client, "api_base", "endpoint")
        )
        backend_title = (
            "Ollama"
            if config.active_backend.lower() == "ollama"
            else config.active_backend
        )
        console.print(f"[danger]Error: {backend_title} service is not reachable at[/] {target_endpoint}")
        return

    features = client.get_model_features(config.default_model)
    has_tools = "Tools" in features

    # Contextual system prompt with local environment and tool capabilities
    now_str = datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
    cwd_str = str(Path.cwd().resolve())
    enhanced_prompt = (
        f"{config.system_prompt}\n"
        f"Environment: Local Time: {now_str}. Working Directory: {cwd_str}.\n"
        "Capabilities & Direct Tool Access:\n"
        "You have full authority and built-in function calling tools to interact directly with the local system: "
        "'create_directory' to create directories anywhere on the filesystem, "
        "'write_file' to write or create code, configuration, or documentation files anywhere on the filesystem, "
        "'list_directory' and 'read_file' for inspecting files and folders, 'get_current_time', 'get_current_directory', "
        "'execute_command', 'get_weather' for real-time weather and temperature, and 'fetch_web' for web pages/GitHub URLs.\n"
        "When the user asks you to create files, write code files, construct a directory structure, check weather, "
        "list or read files/folders, URLs, or time, always invoke the appropriate tools directly instead of declining. "
        "Never say you cannot access files, cannot create files, or are just an AI.\n"
        "When tool results are returned, synthesize the answer directly without boilerplate greetings."
    )

    # Inject isolated active workspace knowledge and instructions
    active_ws = getattr(config, "active_workspace", "default")
    ws_context = load_workspace_context(active_ws)
    if ws_context:
        enhanced_prompt += f"\n\n{ws_context}"

    memory = ConversationMemory(system_prompt=enhanced_prompt)
    session_state = {"id": f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"}

    console.print("[#bbbbbb]Commands: /help, /sessions, /new, /delete, /stats, /model, /clear, /back, /exit[/]\n")

    while True:
        try:
            user_input = questionary.text(
                "You:",
                style=QUESTIONARY_STYLE,
            ).ask()

            if user_input is None:
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                should_exit = _handle_slash_command(
                    user_input, config, client, memory, active_ws, session_state
                )
                if should_exit:
                    break
                continue

            # Resolve model: Auto Router vs static default model (multi-turn history aware)
            active_model = config.default_model
            if config.default_model.lower() == "auto":
                from locallm.core.router import route_prompt
                route_res = route_prompt(user_input, config, client, history=memory.history)
                active_model = route_res.selected_model
                console.print(
                    f"[bold #00d7ff]✦ Auto Router:[/] [bold white]{active_model}[/] "
                    f"[#aaaaaa]({route_res.reason})[/]"
                )

            memory.add_user_message(user_input)

            model_features = client.get_model_features(active_model) if hasattr(client, "get_model_features") else []
            has_tools = "Tools" in model_features

            try:
                _process_assistant_turn(
                    config,
                    client,
                    memory,
                    has_tools,
                    model_name=active_model,
                    session_state=session_state,
                )
                save_workspace_session(
                    active_ws,
                    session_state["id"],
                    memory,
                    metadata={"type": "assistant", "model": active_model},
                )
            except Exception as exc:
                console.print(f"[danger]Generation error:[/] {exc}")

        except KeyboardInterrupt:
            console.print("\n[#aaaaaa]Chat interrupted.[/]")
            break


def _process_assistant_turn(
    config: LocaLLMConfig,
    client: Any,
    memory: ConversationMemory,
    has_tools: bool,
    model_name: Optional[str] = None,
    session_state: Optional[Dict[str, Any]] = None,
) -> None:
    """Process an autonomous multi-step agent turn with native tool calling and context usage telemetry."""
    context_limit = getattr(config, "context_window", 8192)
    stats: Dict[str, Any] = {}
    target_model = model_name or config.default_model
    active_ws = getattr(config, "active_workspace", "default")
    permission_policy = getattr(config, "agent_permission_policy", "ask")

    MAX_TOOL_STEPS = 25

    if has_tools:
        step = 0
        executed_any_tool = False

        while step < MAX_TOOL_STEPS:
            step += 1
            turn_msg = None
            spinner_msg = "locaLLM is thinking..." if step == 1 else f"locaLLM is planning step {step}..."
            with thinking_spinner(spinner_msg):
                try:
                    turn_msg = client.chat_turn(
                        model=target_model,
                        messages=memory.get_messages(),
                        tools=ASSISTANT_TOOLS,
                        temperature=config.temperature,
                        num_ctx=context_limit,
                        stats_out=stats,
                    )
                except Exception:
                    turn_msg = None

            if not turn_msg:
                break

            tool_calls = turn_msg.get("tool_calls")
            if tool_calls:
                executed_any_tool = True
                memory.history.append(turn_msg)

                for idx, tc in enumerate(tool_calls):
                    func_name = tc.get("function", {}).get("name", "")
                    func_args = tc.get("function", {}).get("arguments", {})
                    tc_id = tc.get("id") or f"call_{step}_{idx}"
                    if isinstance(func_args, str):
                        try:
                            func_args = json.loads(func_args)
                        except Exception:
                            func_args = {}

                    with thinking_spinner(f"locaLLM is executing {func_name}..."):
                        obs = execute_tool(
                            func_name,
                            func_args,
                            permission_policy=permission_policy,
                            interactive=True,
                            session_state=session_state,
                            workspace_name=active_ws,
                        )

                    memory.history.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": obs,
                    })

                # Loop back: let LLM examine tool observations and plan next step or conclude
                continue

            # No tool calls: model returned final answer
            content = turn_msg.get("content", "")
            if content and content.strip():
                print_assistant_response(content, stats=stats, context_limit=context_limit)
                memory.add_assistant_message(content)
                return
            else:
                # Empty content without tool calls: break to fallback
                break

        # If tools were executed but model finished with empty text, request a final completion summary
        if executed_any_tool:
            with thinking_spinner("locaLLM is summarizing actions..."):
                try:
                    summary_turn = client.chat_turn(
                        model=target_model,
                        messages=memory.get_messages() + [
                            {"role": "user", "content": "All requested actions have been executed. Provide a clear summary of the completed tasks."}
                        ],
                        temperature=config.temperature,
                        num_ctx=context_limit,
                        stats_out=stats,
                    )
                    content = summary_turn.get("content", "")
                    if content and content.strip():
                        print_assistant_response(content, stats=stats, context_limit=context_limit)
                        memory.add_assistant_message(content)
                        return
                except Exception:
                    pass

    # Direct token streaming fallback
    stream_stats: Dict[str, Any] = {}
    tokens = client.chat_stream(
        model=target_model,
        messages=memory.get_messages(),
        temperature=config.temperature,
        num_ctx=context_limit,
        stats_out=stream_stats,
    )
    response = stream_assistant_response(tokens, stats=stream_stats, context_limit=context_limit)
    if not response or not response.strip():
        with thinking_spinner("locaLLM is thinking..."):
            fallback_turn = client.chat_turn(
                model=target_model,
                messages=memory.get_messages(),
                temperature=config.temperature,
                num_ctx=context_limit,
                stats_out=stream_stats,
            )
        content = fallback_turn.get("content", "")
        if content and content.strip():
            print_assistant_response(content, stats=stream_stats, context_limit=context_limit)
            memory.add_assistant_message(content)
            return
        else:
            console.print("[yellow]Notice: Model could not generate a response. Please try again.[/]\n")
            return

    memory.add_assistant_message(response)


def _handle_slash_command(
    command: str,
    config: LocaLLMConfig,
    client: OllamaClient,
    memory: ConversationMemory,
    active_ws: str,
    session_state: Dict[str, str],
) -> bool:
    """Handle chat slash commands. Returns True if loop should terminate."""
    cmd = command.lower().strip()

    if cmd in ("/exit", "/quit"):
        raise SystemExit(0)

    if cmd in ("/back", "/menu"):
        return True

    if cmd == "/help":
        print_help_commands()
        return False

    if cmd == "/clear":
        memory.clear()
        save_workspace_session(
            active_ws,
            session_state["id"],
            memory,
            metadata={"type": "assistant", "model": config.default_model},
        )
        print_system_info("Conversation history cleared.")
        return False

    if cmd == "/new":
        session_state["id"] = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        memory.clear()
        print_system_info(f"Started fresh session '{session_state['id']}'. Previous chat archived.")
        return False

    if cmd == "/sessions":
        _manage_sessions(active_ws, memory, session_state, config)
        return False

    if cmd in ("/delete", "/del", "/delete-session", "/rm"):
        _delete_session_dialog(active_ws, memory, session_state)
        return False

    if cmd == "/stats":
        _show_session_stats(config, client, memory)
        return False

    if cmd == "/system":
        _change_system_prompt(config, memory)
        return False

    if cmd == "/model":
        _switch_model(config, client)
        return False

    print_system_info(f"Unknown command: '{command}'. Type /help for options.")
    return False


def _delete_session_dialog(
    active_ws: str,
    memory: ConversationMemory,
    session_state: Dict[str, str],
) -> None:
    """Prompt user to delete current active session, a specific session file, or all sessions."""
    choice = questionary.select(
        "Delete chat history:",
        choices=[
            "Delete Current Active Session",
            "Select Saved Session to Delete",
            "Delete All Saved Sessions in Workspace",
            "Cancel",
        ],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not choice or choice == "Cancel":
        return

    if choice == "Delete Current Active Session":
        cur_id = session_state.get("id", "")
        if cur_id:
            delete_workspace_session(active_ws, cur_id)
        memory.clear()
        session_state["id"] = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print_system_info(f"Active session '{cur_id}' deleted. Started fresh session.")
        return

    if choice == "Select Saved Session to Delete":
        sessions = list_workspace_sessions(active_ws)
        if not sessions:
            print_system_info(f"No saved sessions found in workspace '{active_ws}'.")
            return

        del_choices = [s["session_id"] for s in sessions] + ["Cancel"]
        target_id = questionary.select(
            "Select session file to delete:",
            choices=del_choices,
            style=QUESTIONARY_STYLE,
        ).ask()

        if not target_id or target_id == "Cancel":
            return

        ok = delete_workspace_session(active_ws, target_id)
        if ok:
            if session_state.get("id") == target_id:
                memory.clear()
                session_state["id"] = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print_system_info(f"Session '{target_id}' deleted successfully.")
        else:
            print_system_info(f"Failed to delete session '{target_id}'.")
        return

    if choice == "Delete All Saved Sessions in Workspace":
        confirm = questionary.confirm(
            f"Are you sure you want to delete ALL saved sessions in workspace '{active_ws}'?",
            default=False,
            style=QUESTIONARY_STYLE,
        ).ask()
        if confirm:
            deleted_count = clear_all_workspace_sessions(active_ws)
            memory.clear()
            session_state["id"] = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print_system_info(f"Deleted {deleted_count} session file(s) in workspace '{active_ws}'. Started fresh session.")


def _manage_sessions(
    active_ws: str,
    memory: ConversationMemory,
    session_state: Dict[str, str],
    config: LocaLLMConfig,
) -> None:
    """Display saved workspace sessions and allow user to view, resume, or delete them."""
    sessions = list_workspace_sessions(active_ws)
    if not sessions:
        print_system_info(f"No saved sessions found in workspace '{active_ws}'.")
        return

    table = Table(title=f"Saved Sessions in Workspace: [bold cyan]{active_ws}[/]", border_style="cyan")
    table.add_column("Session ID", style="bold cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Turns", justify="right")
    table.add_column("Updated At", style="#aaaaaa")
    table.add_column("Last Snippet", style="white", max_width=40)

    for s in sessions[:15]:
        table.add_row(
            s["session_id"],
            s.get("type", "chat"),
            str(s.get("message_count", 0)),
            s.get("updated_at", "")[:19].replace("T", " "),
            s.get("last_snippet", ""),
        )
    console.print(table)
    console.print()

    choices = (
        [f"Resume: {s['session_id']}" for s in sessions[:15]]
        + ["Delete a Saved Session", "Delete All Saved Sessions", "Start New Session", "Cancel"]
    )
    action = questionary.select(
        "Select session action:",
        choices=choices,
        style=QUESTIONARY_STYLE,
    ).ask()

    if not action or action == "Cancel":
        return

    if action == "Start New Session":
        session_state["id"] = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        memory.clear()
        print_system_info(f"Started fresh session '{session_state['id']}'.")
        return

    if action == "Delete a Saved Session":
        del_choices = [s["session_id"] for s in sessions] + ["Cancel"]
        target_id = questionary.select(
            "Select session to delete:",
            choices=del_choices,
            style=QUESTIONARY_STYLE,
        ).ask()
        if target_id and target_id != "Cancel":
            ok = delete_workspace_session(active_ws, target_id)
            if ok:
                if session_state.get("id") == target_id:
                    memory.clear()
                    session_state["id"] = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                print_system_info(f"Session '{target_id}' deleted successfully.")
            else:
                print_system_info(f"Failed to delete session '{target_id}'.")
        return

    if action == "Delete All Saved Sessions":
        confirm = questionary.confirm(
            f"Are you sure you want to delete ALL saved sessions in workspace '{active_ws}'?",
            default=False,
            style=QUESTIONARY_STYLE,
        ).ask()
        if confirm:
            deleted_count = clear_all_workspace_sessions(active_ws)
            memory.clear()
            session_state["id"] = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print_system_info(f"Deleted {deleted_count} session file(s) in workspace '{active_ws}'.")
        return

    if action.startswith("Resume: "):
        selected_id = action.replace("Resume: ", "").strip()
        loaded = load_workspace_session(active_ws, selected_id)
        if loaded:
            memory.history = list(loaded.history)
            session_state["id"] = selected_id
            print_system_info(f"Resumed session '{selected_id}' ({len(memory.history)} messages).")
        else:
            print_system_info(f"Failed to load session '{selected_id}'.")


def _show_session_stats(
    config: LocaLLMConfig,
    client: Any,
    memory: ConversationMemory,
) -> None:
    """Display runtime session, model telemetry, and hardware metrics."""
    gpu = get_gpu_info()
    if config.default_model.lower() == "auto":
        features = ["Auto Router (Dynamic Dispatch)"]
        details = {"parameter_size": "Dynamic", "quantization_level": "Dynamic", "format": "Dynamic"}
    else:
        info = client.get_model_info(config.default_model) if hasattr(client, "get_model_info") else {}
        details = info.get("details", {})
        features = client.get_model_features(config.default_model) if hasattr(client, "get_model_features") else []
    ctx_limit = getattr(config, "context_window", 8192)

    table = Table(border_style="cyan", header_style="bold cyan")
    table.add_column("Metric", style="bold white")
    table.add_column("Value")

    table.add_row("Active Model", f"[bold cyan]{config.default_model}[/]")
    table.add_row("Capabilities", f"[bold green]{', '.join(features)}[/]")
    table.add_row("Context Window", f"{ctx_limit:,} tokens")
    table.add_row("Parameter Size", str(details.get("parameter_size", "N/A")))
    table.add_row("Quantization", str(details.get("quantization_level", "N/A")))
    table.add_row("Format", str(details.get("format", "gguf")))

    if gpu:
        free_gb = gpu.free_vram_mb / 1024
        total_gb = gpu.total_vram_mb / 1024
        table.add_row("GPU Hardware", f"{gpu.name} ({free_gb:.1f} GB Free / {total_gb:.1f} GB Total)")
    else:
        table.add_row("GPU Hardware", "CPU Mode (No GPU detected)")

    target_endpoint = (
        config.ollama_host
        if config.active_backend.lower() == "ollama"
        else getattr(client, "api_base", config.ollama_host)
    )
    table.add_row("Conversation Turns", f"{len(memory.history)} messages in memory")
    table.add_row("Inference Endpoint", target_endpoint)
    table.add_row("Sampling Temperature", str(config.temperature))

    console.print()
    console.print(Panel(table, title="[bold cyan]Session Telemetry & Model Stats[/]", border_style="cyan"))
    console.print()


def _switch_model(config: LocaLLMConfig, client: Any) -> None:
    """Prompt user to select another active model."""
    models = client.list_models()
    backend_title = (
        "Ollama"
        if config.active_backend.lower() == "ollama"
        else config.active_backend
    )
    if not models:
        console.print(f"[warning]No models found on {backend_title} server.[/]")
        return

    choices = ["Auto (Smart Router)"] + [m.get("name") or m.get("id") for m in models]
    choices = [c for c in choices if c]
    chosen = questionary.select(
        "Select active model:",
        choices=choices,
        style=QUESTIONARY_STYLE,
    ).ask()

    if chosen:
        if chosen == "Auto (Smart Router)":
            config.default_model = "auto"
        else:
            config.default_model = chosen
            if config.active_backend.lower() == "ollama":
                config.ollama_model = chosen
            else:
                from locallm.config import get_custom_platform
                platform = get_custom_platform(config, config.active_backend)
                if platform:
                    platform.default_model = chosen
        save_config(config)
        console.print(f"[success]Active model switched to:[/] [bold cyan]{config.default_model}[/]")


def _change_system_prompt(config: LocaLLMConfig, memory: ConversationMemory) -> None:
    """Prompt user to edit current system prompt."""
    console.print(f"[dim]Current system prompt:[/] {config.system_prompt}")
    new_prompt = questionary.text(
        "Enter new system prompt (leave blank to cancel):",
        style=QUESTIONARY_STYLE,
    ).ask()

    if new_prompt and new_prompt.strip():
        config.system_prompt = new_prompt.strip()
        memory.set_system_prompt(config.system_prompt)
        save_config(config)
        print_system_info("System prompt updated and saved.")
