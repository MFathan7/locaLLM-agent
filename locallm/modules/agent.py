"""Autonomous agent engine with unified native tool calling and ReAct execution loop."""

from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import questionary
from rich.panel import Panel
from locallm.config import LocaLLMConfig, save_config
from locallm.core.tools import (
    describe_tool_action,
    execute_tool,
    extract_fallback_tool_calls,
    format_live_tool_report,
    get_all_assistant_tools,
    resolve_smart_path,
)
from locallm.core.workspace import load_workspace_context
from locallm.ui.spinner import thinking_spinner
from locallm.ui.theme import QUESTIONARY_STYLE, console, get_theme_palette


class ReActAgent:
    """Autonomous agent engine supporting native function calling and ReAct fallback."""

    def __init__(
        self,
        config: LocaLLMConfig,
        client: Any,
        model_name: Optional[str] = None,
        max_steps: Optional[int] = None,
        interactive: bool = True,
    ):
        self.config = config
        self.client = client
        self.model_name = model_name or config.default_model
        self.max_steps = max_steps or getattr(config, "agent_max_steps", 25)
        self.interactive = interactive

    def run_task(self, task_instruction: str) -> None:
        """Execute a task through multi-step autonomous planning and tool execution."""
        palette = get_theme_palette(getattr(self.config, "ui_theme", "cyber_neon"))
        console.print(Panel(
            task_instruction,
            title=f"[bold {palette.primary}]⟦{palette.icon} Autonomous Agent Task⟧[/]",
            box=palette.box_style,
            border_style=palette.border_style,
        ))

        active_ws = getattr(self.config, "active_workspace", "default")
        ws_context = load_workspace_context(active_ws)
        current_tools = get_all_assistant_tools(active_ws)
        tool_names = {t.get("function", {}).get("name") for t in current_tools if isinstance(t, dict)}
        permission_policy = getattr(self.config, "agent_permission_policy", "ask")
        context_limit = getattr(self.config, "context_window", 8192)

        now_str = datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
        cwd_str = str(Path.cwd().resolve())

        system_content = (
            "You are locaLLM Autonomous Agent, a disciplined and highly capable local AI software engineer and system operator.\n"
            "Your task is to autonomously execute the user's objective by planning, inspecting, and using tools until the goal is fully accomplished.\n\n"
            f"Environment: Local Time: {now_str}. Working Directory: {cwd_str}.\n\n"
            "Core Directives:\n"
            "1. Autonomous Action: Use tools directly to inspect the environment, fetch web data, read/write files, and execute commands. Never instruct the user to perform manual work when tools can perform the action.\n"
            "2. Grounding: Verify facts through tool output before concluding.\n"
            "3. Stopping Condition: When the objective is completely satisfied, provide a clear, comprehensive final summary of the accomplished tasks and findings.\n"
            "4. Read-Only vs Mutating Discipline: If the user's objective only asks to find, locate, search, check, or report file paths, existence, or metadata, NEVER invoke write_file, create_directory, or modifying commands. Use resolve_path, list_directory, or read_file exclusively."
        )
        if ws_context:
            system_content += f"\n\n{ws_context}"

        history: List[Dict[str, Any]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"Task: {task_instruction}"},
        ]
        consecutive_failures: Dict[str, int] = {}
        session_state: Dict[str, Any] = {"id": f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"}
        executed_actions: List[Dict[str, Any]] = []

        step = 0
        total_steps = self.max_steps

        while step < total_steps:
            step += 1
            turn_msg: Optional[Dict[str, Any]] = None

            spinner_label = (
                f"Agent is planning step {step}/{total_steps}..."
                if step == 1
                else f"Agent is evaluating observations & planning next action (step {step}/{total_steps})..."
            )

            with thinking_spinner(spinner_label, style=f"bold {palette.accent}"):
                try:
                    if hasattr(self.client, "chat_turn"):
                        turn_msg = self.client.chat_turn(
                            model=self.model_name,
                            messages=history,
                            tools=current_tools,
                            temperature=0.2,
                            num_ctx=context_limit,
                        )
                    else:
                        # Defensive fallback for simple chat client
                        raw_reply = self.client.chat(
                            model=self.model_name,
                            messages=history,
                            temperature=0.2,
                        )
                        turn_msg = {"role": "assistant", "content": raw_reply}
                except Exception as exc:
                    console.print(f"[danger]Agent error communicating with model:[/] {exc}")
                    if executed_actions:
                        completed_items = []
                        for act in executed_actions:
                            status_icon = "✘" if act["is_error"] else "✔"
                            t_name = act["tool"]
                            t_args = act["args"]
                            if t_name == "write_file":
                                detail = f"Written file: {t_args.get('path', '')}"
                            elif t_name == "create_directory":
                                detail = f"Created directory: {t_args.get('path', '')}"
                            elif t_name == "execute_command":
                                detail = f"Executed command: {t_args.get('command', '')}"
                            elif t_name == "fetch_web":
                                detail = f"Fetched URL: {t_args.get('url', '')}"
                            elif t_name == "read_file":
                                detail = f"Read file: {t_args.get('path', '')}"
                            else:
                                detail = f"Executed tool '{t_name}'"
                            completed_items.append(f"  {status_icon} [bold]{detail}[/]")

                        report = "\n".join(completed_items)
                        console.print(Panel(
                            f"[bold yellow]Notice:[/] Model communication timed out or encountered an issue, but the following actions were already executed successfully:\n\n{report}\n\n[dim]All changes performed by the agent before this interruption remain saved on disk.[/]",
                            title=f"[bold {palette.accent}]⟦{palette.icon} Actions Completed Before Interruption⟧[/]",
                            box=palette.box_style,
                            border_style=palette.border_style,
                        ))
                    return

            if not turn_msg:
                console.print("[warning]Model returned empty turn response.[/]")
                break

            tool_calls = turn_msg.get("tool_calls")
            content = turn_msg.get("content", "")

            # Recover fallback tool calls from text stream if native tool calls not emitted
            if not tool_calls and content:
                recovered = extract_fallback_tool_calls(content, tool_names)
                if recovered:
                    tool_calls = recovered
                    turn_msg["tool_calls"] = recovered

            # Execute tool calls if present
            if tool_calls:
                history.append(turn_msg)
                should_trip_circuit = False

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
                    console.print(
                        f"[bold {palette.accent}]⟦{palette.icon} STEP {step}/{total_steps}⟧[/] "
                        f"[bold {palette.primary}]{func_name}[/] [dim]{json.dumps(func_args)}[/]"
                    )

                    with thinking_spinner(action_label, style=f"bold {palette.primary}"):
                        observation = execute_tool(
                            func_name,
                            func_args,
                            permission_policy=permission_policy,
                            interactive=self.interactive,
                            session_state=session_state,
                            workspace_name=active_ws,
                        )

                    console.print(format_live_tool_report(func_name, func_args, observation))

                    # Circuit breaker check: track identical consecutive failures
                    call_sig = f"{func_name}:{json.dumps(func_args, sort_keys=True)}"
                    is_err = observation.startswith("Error:") or observation.startswith("Failed") or "Exception:" in observation
                    if is_err:
                        consecutive_failures[call_sig] = consecutive_failures.get(call_sig, 0) + 1
                    else:
                        consecutive_failures[call_sig] = 0

                    executed_actions.append({
                        "step": step,
                        "tool": func_name,
                        "args": func_args,
                        "observation": observation,
                        "is_error": is_err,
                    })

                    if consecutive_failures[call_sig] >= 2:
                        console.print(
                            f"[warning]Circuit breaker tripped: Tool '{func_name}' failed repeatedly with identical parameters. "
                            f"Halting action loop to prevent token exhaustion.[/]"
                        )
                        obs_to_send = f"{observation}\n[System Notice: Action halted by circuit breaker after 2 consecutive identical failures. Please revise your approach or summarize what has been accomplished.]"
                        should_trip_circuit = True
                    else:
                        obs_to_send = observation

                    history.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": obs_to_send,
                    })

                if should_trip_circuit:
                    break

                continue

            # No tool calls: model returned final answer
            if content and content.strip():
                final_answer_text = self._extract_final_answer(content)
                console.print(Panel(
                    final_answer_text,
                    title=f"[bold {palette.success}]⟦{palette.icon} Task Completed⟧[/]",
                    box=palette.box_style,
                    border_style=palette.border_style,
                ))
                return

            # Check if step limit reached
            if step >= total_steps:
                if self.interactive:
                    console.print(f"\n[bold yellow]✦ Step Limit Notice:[/] Agent has executed [bold cyan]{total_steps}[/] steps.")
                    extend = questionary.confirm(
                        f"Extend execution for 10 more steps?",
                        default=True,
                        style=QUESTIONARY_STYLE,
                    ).ask()
                    if extend:
                        total_steps += 10
                        continue
                break

        # Max step limit reached or broken: synthesize final summary from observations
        console.print(f"\n[warning]Step limit ({total_steps}) reached. Synthesizing completion summary...[/]")
        with thinking_spinner("Agent is synthesizing final progress summary...", style=f"bold {palette.accent}"):
            try:
                summary_msg = self.client.chat_turn(
                    model=self.model_name,
                    messages=history + [
                        {
                            "role": "user",
                            "content": "All execution steps are finished. Provide a clear, comprehensive final summary of the task findings, files modified/created, and current status based on the observations collected.",
                        }
                    ],
                    temperature=0.2,
                    num_ctx=context_limit,
                )
                final_text = (summary_msg.get("content") or "").strip()
                if not final_text:
                    final_text = "Task concluded upon reaching the configured maximum step limit."
            except Exception:
                if executed_actions:
                    act_summary = "\n".join(
                        f"• {a['tool']}: {a['args'].get('path') or a['args'].get('command') or a['args'].get('url') or ''}"
                        for a in executed_actions if not a.get("is_error")
                    )
                    final_text = f"Task execution finished. Actions performed:\n{act_summary}"
                else:
                    final_text = "Task concluded upon reaching the configured maximum step limit."

        console.print(Panel(
            final_text,
            title=f"[bold {palette.success}]⟦{palette.icon} Task Progress Summary⟧[/]",
            box=palette.box_style,
            border_style=palette.border_style,
        ))

    def _extract_final_answer(self, text: str) -> str:
        """Extract clean text or JSON final_answer field if present."""
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        cand = match.group(1) if match else text.strip()
        try:
            parsed = json.loads(cand)
            if isinstance(parsed, dict) and "final_answer" in parsed:
                return str(parsed["final_answer"])
        except Exception:
            pass
        return text.strip()


AgentEngine = ReActAgent


def configure_permission_policy(config: LocaLLMConfig) -> None:

    """Prompt user to configure agent permission policy for mutating actions."""
    current = getattr(config, "agent_permission_policy", "ask").lower()
    choice = questionary.select(
        "Agent Permission Policy (for write_file, create_directory, execute_command):",
        choices=[
            "always_allow (Unrestricted execution)",
            "ask (Prompt for confirmation before mutating actions)",
            "deny (Read-only mode; block file creation and shell execution)",
            "Back",
        ],
        style=QUESTIONARY_STYLE,
    ).ask()

    if choice is None or choice == "Back":
        return

    new_policy = choice.split(" ")[0].strip()
    config.agent_permission_policy = new_policy
    config.agent_auto_approve_commands = (new_policy == "always_allow")
    save_config(config)
    console.print(f"[success]Agent permission policy updated to: [bold cyan]{new_policy}[/][/]\n")


def toggle_agent_auto_approve(config: LocaLLMConfig) -> None:
    """Toggle whether agent automatically executes shell commands without confirmation."""
    current = getattr(config, "agent_permission_policy", "ask")
    if current == "always_allow":
        config.agent_permission_policy = "ask"
        config.agent_auto_approve_commands = False
    else:
        config.agent_permission_policy = "always_allow"
        config.agent_auto_approve_commands = True
    save_config(config)
    console.print(f"[success]Agent permission policy is now: [bold cyan]{config.agent_permission_policy}[/][/]\n")


def run_agent_menu(config: LocaLLMConfig, client: Any) -> None:
    """Interactive submenu for Autonomous Agent & Automation."""
    while True:
        policy = getattr(config, "agent_permission_policy", "ask")
        choice = questionary.select(
            "Agent & Automation:",
            choices=[
                "Run Agent Task",
                f"Permission Policy (Current: {policy})",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice == "Run Agent Task":
            run_agent_interactive(config, client)
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        elif choice.startswith("Permission Policy"):
            configure_permission_policy(config)


def run_agent_interactive(config: LocaLLMConfig, client: Any) -> None:
    """Interactive prompt to launch an agent task."""
    if not client.is_connected():
        target_endpoint = (
            config.ollama_host
            if config.active_backend.lower() == "ollama"
            else getattr(client, "api_base", "endpoint")
        )
        console.print(f"[danger]Error: LLM service is not reachable at[/] {target_endpoint}")
        return

    active_ws = getattr(config, "active_workspace", "default")
    policy = getattr(config, "agent_permission_policy", "ask")
    model_display = (
        "[bold #00d7ff]Auto (Smart Router)[/]"
        if config.default_model.lower() == "auto"
        else f"[bold green]{config.default_model}[/]"
    )
    max_steps_val = getattr(config, "agent_max_steps", 25)
    console.print(
        f"[#aaaaaa]Model:[/] {model_display} "
        f"[#aaaaaa]| Workspace:[/] [bold cyan]{active_ws}[/] "
        f"[#aaaaaa]| Policy:[/] [bold cyan]{policy}[/] "
        f"[#aaaaaa]| Max Steps:[/] [bold cyan]{max_steps_val}[/]\n"
    )

    task = questionary.text(
        "Enter your task or goal for the Agent (leave blank to cancel):",
        style=QUESTIONARY_STYLE,
    ).ask()

    if not task or not task.strip():
        console.print("[#aaaaaa]Task entry cancelled.[/]")
        return

    target_model = config.default_model
    if config.default_model.lower() == "auto":
        from locallm.core.router import route_prompt
        route = route_prompt(task.strip(), config, client, is_agent_task=True)
        target_model = route.selected_model
        console.print(f"[bold #00d7ff]✦ Auto Router:[/] {route.selected_model} [dim]({route.reason})[/]\n")

    engine = AgentEngine(config, client, model_name=target_model, max_steps=max_steps_val, interactive=True)
    engine.run_task(task.strip())
