"""One-shot prompt execution for command line automation with native tool calling."""

from datetime import datetime
import json
from pathlib import Path
import sys
from locallm.config import LocaLLMConfig
from locallm.core.ollama_client import OllamaClient
from locallm.core.tools import ASSISTANT_TOOLS, describe_tool_action, execute_tool, format_live_tool_report
from locallm.core.workspace import load_workspace_context
from locallm.ui.chat_view import stream_assistant_response
from locallm.ui.spinner import thinking_spinner
from locallm.ui.theme import console


def execute_prompt(prompt: str, config: LocaLLMConfig, client: OllamaClient) -> None:
    """Execute a single prompt from CLI and stream the result to console with tool execution."""
    if not client.is_connected():
        console.print(f"[danger]Error: Ollama service is not reachable at[/] {config.ollama_host}")
        sys.exit(1)

    now_str = datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
    cwd_str = str(Path.cwd().resolve())
    context_system = (
        f"{config.system_prompt}\n"
        f"Environment: Local Time: {now_str}. Working Directory: {cwd_str}.\n"
        "Capabilities & Direct Tool Access:\n"
        "You have full authority and built-in function calling tools to interact directly with the local system: "
        "'create_directory' to create directories anywhere on the filesystem, "
        "'write_file' to write or create code, configuration, or documentation files anywhere on the filesystem, "
        "'list_directory' and 'read_file' for inspecting files and folders, 'get_current_time', 'get_current_directory', "
        "'execute_command', 'get_weather' for real-time weather and temperature, and 'fetch_web' for web pages/GitHub URLs.\n"
        "CRITICAL AUTONOMOUS EXECUTION DIRECTIVE:\n"
        "When the user asks to create, write, modify, generate, or execute any files, directories, scripts, or system tasks:\n"
        "- DO NOT provide manual terminal, shell, or command-prompt instructions for the user to run themselves.\n"
        "- DO NOT ask or expect the user to manually create directories or save files.\n"
        "- You MUST directly invoke the appropriate tools ('create_directory', 'write_file', 'execute_command') "
        "via native function calling to perform the requested actions immediately on the local system.\n"
        "Never say you cannot access files, cannot create files, or are just an AI.\n"
        "When tool results are returned, synthesize the answer directly without boilerplate greetings."
    )

    ws_context = load_workspace_context(getattr(config, "active_workspace", "default"))
    if ws_context:
        context_system += f"\n\n{ws_context}"

    messages = [
        {"role": "system", "content": context_system},
        {"role": "user", "content": prompt},
    ]

    target_model = config.default_model
    if config.default_model.lower() == "auto":
        from locallm.core.router import route_prompt
        route = route_prompt(prompt, config, client)
        target_model = route.selected_model
        console.print(f"[bold #00d7ff]✦ Auto Router:[/] {route.selected_model} [dim]({route.reason})[/]\n")

    features = client.get_model_features(target_model)
    has_tools = "Tools" in features
    context_limit = getattr(config, "context_window", 8192)

    try:
        stats: dict = {}
        if has_tools:
            MAX_TOOL_STEPS = 25
            step = 0
            executed_any_tool = False
            active_ws = getattr(config, "active_workspace", "default")
            permission_policy = getattr(config, "agent_permission_policy", "ask")

            while step < MAX_TOOL_STEPS:
                step += 1
                turn_msg = None
                spinner_text = (
                    "locaLLM is thinking..."
                    if step == 1
                    else "locaLLM is analyzing results & planning next action..."
                )
                with thinking_spinner(spinner_text):
                    try:
                        turn_msg = client.chat_turn(
                            model=target_model,
                            messages=messages,
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
                if not tool_calls and turn_msg.get("content"):
                    from locallm.core.tools import extract_fallback_tool_calls
                    tool_names = {t.get("function", {}).get("name") for t in ASSISTANT_TOOLS}
                    recovered = extract_fallback_tool_calls(turn_msg.get("content", ""), tool_names)
                    if recovered:
                        tool_calls = recovered
                        turn_msg["tool_calls"] = recovered

                if tool_calls:
                    executed_any_tool = True
                    messages.append(turn_msg)
                    for idx, tc in enumerate(tool_calls):
                        func_name = tc.get("function", {}).get("name", "")
                        func_args = tc.get("function", {}).get("arguments", {})
                        tc_id = tc.get("id") or f"call_{step}_{idx}"
                        if isinstance(func_args, str):
                            try:
                                func_args = json.loads(func_args)
                            except Exception:
                                func_args = {}
                        action_label = describe_tool_action(func_name, func_args)
                        with thinking_spinner(action_label):
                            obs = execute_tool(
                                func_name,
                                func_args,
                                permission_policy=permission_policy,
                                interactive=True,
                                workspace_name=active_ws,
                            )
                        console.print(format_live_tool_report(func_name, func_args, obs))
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": obs,
                        })
                    continue

                content = turn_msg.get("content", "")
                if content and content.strip():
                    console.print("[bold green]locaLLM >[/] ", end="")
                    console.print(content)
                    console.print()
                    from locallm.ui.chat_view import render_response_stats
                    render_response_stats(stats, context_limit=context_limit)
                    return
                else:
                    break

            if executed_any_tool:
                with thinking_spinner("locaLLM is summarizing completed actions..."):
                    try:
                        summary_turn = client.chat_turn(
                            model=target_model,
                            messages=messages + [
                                {"role": "user", "content": "All requested actions have been executed. Provide a clear summary of the completed tasks."}
                            ],
                            temperature=config.temperature,
                            num_ctx=context_limit,
                            stats_out=stats,
                        )
                        content = summary_turn.get("content", "")
                        if content and content.strip():
                            console.print("[bold green]locaLLM >[/] ", end="")
                            console.print(content)
                            console.print()
                            from locallm.ui.chat_view import render_response_stats
                            render_response_stats(stats, context_limit=context_limit)
                            return
                    except Exception:
                        pass

        stream_stats = {}
        tokens = client.chat_stream(
            model=target_model,
            messages=messages,
            temperature=config.temperature,
            num_ctx=context_limit,
            stats_out=stream_stats,
        )
        stream_assistant_response(tokens, stats=stream_stats, context_limit=context_limit)
    except Exception as exc:
        console.print(f"[danger]Execution error:[/] {exc}")
        sys.exit(1)
