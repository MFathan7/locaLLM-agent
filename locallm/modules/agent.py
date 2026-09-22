"""Autonomous agent engine with ReAct tool execution loop."""

import json
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Optional
import httpx
import questionary
from rich.panel import Panel
from locallm.config import LocaLLMConfig, save_config
from locallm.core.ollama_client import OllamaClient
from locallm.core.tools import resolve_smart_path
from locallm.core.workspace import load_workspace_context
from locallm.ui.theme import QUESTIONARY_STYLE, console, get_theme_palette

SYSTEM_AGENT_PROMPT = """You are an autonomous AI agent with local tools to complete user tasks.
To use a tool, respond ONLY in this JSON format:
```json
{
  "thought": "Reasoning why this tool is needed",
  "tool": "tool_name",
  "args": {"arg_key": "arg_value"}
}
```

When the task is complete, or if no tool is needed, respond with:
```json
{
  "thought": "I have completed the task or have final information",
  "final_answer": "Summary of what was accomplished"
}
```

Available tools:
- list_directory: {"path": "."}
- read_file: {"path": "filename"}
- write_file: {"path": "filename", "content": "text content"}
- create_directory: {"path": "dirname"}
- execute_command: {"command": "shell command"}
- fetch_web: {"url": "https://example.com"}

Always explain your thought before taking action.
When done, output final_answer with the result.
"""


class ReActAgent:
    """ReAct execution loop using local Ollama model."""

    def __init__(self, config: LocaLLMConfig, client: OllamaClient, model_name: Optional[str] = None):

        self.config = config
        self.client = client
        self.model_name = model_name or config.default_model
        self.max_steps = 10

    def run_task(self, task_instruction: str) -> None:
        """Execute a task through multi-step reasoning."""
        palette = get_theme_palette(getattr(self.config, "ui_theme", "cyber_neon"))
        console.print(Panel(
            task_instruction,
            title=f"[bold {palette.primary}]⟦{palette.icon} Autonomous Agent Task⟧[/]",
            box=palette.box_style,
            border_style=palette.border_style,
        ))

        ws_context = load_workspace_context(getattr(self.config, "active_workspace", "default"))
        system_content = SYSTEM_AGENT_PROMPT
        if ws_context:
            system_content += f"\n\n{ws_context}"

        history: List[Dict[str, str]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"Task: {task_instruction}"},
        ]
        consecutive_failures: Dict[str, int] = {}

        for step in range(1, self.max_steps + 1):
            from locallm.ui.spinner import thinking_spinner

            try:
                with thinking_spinner(f"Agent is planning step {step}/{self.max_steps}...", style="bold magenta"):
                    response = self.client.chat(
                        model=self.model_name,
                        messages=history,
                        temperature=0.2,
                    )
            except Exception as exc:
                console.print(f"[danger]Agent error communicating with model:[/] {exc}")
                return

            action_data = self._extract_json(response)
            if not action_data:
                console.print(Panel(response, title="[dim]Model Note[/]", box=palette.box_style, border_style="dim"))
                history.append({"role": "assistant", "content": response})
                history.append({
                    "role": "user",
                    "content": "Please format your output strictly as a JSON object inside ```json ... ```.",
                })
                continue

            thought = action_data.get("thought", "")
            if thought:
                console.print(f"[dim white]Thought:[/] {thought}")

            if "final_answer" in action_data:
                console.print(Panel(
                    action_data["final_answer"],
                    title=f"[bold {palette.success}]⟦{palette.icon} Task Completed⟧[/]",
                    box=palette.box_style,
                    border_style=palette.border_style,
                ))
                return

            tool_name = action_data.get("tool")
            args = action_data.get("args", {})

            console.print(f"[bold {palette.accent}]⟦{palette.icon} STEP {step}/{self.max_steps}⟧[/] [bold {palette.primary}]{tool_name}[/] [dim]{json.dumps(args)}[/]")

            # Execute tool
            observation = self._execute_tool(tool_name, args)
            obs_preview = observation[:180] + "..." if len(observation) > 180 else observation
            console.print(f"[{palette.success}]✔ Observation:[/] {obs_preview}")

            # Circuit breaker check: track identical consecutive failures
            call_sig = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
            is_err = observation.startswith("Error:") or observation.startswith("Failed") or "Exception:" in observation
            if is_err:
                consecutive_failures[call_sig] = consecutive_failures.get(call_sig, 0) + 1
            else:
                consecutive_failures[call_sig] = 0

            if consecutive_failures[call_sig] >= 2:
                console.print(f"[warning]Circuit breaker tripped: Tool '{tool_name}' failed repeatedly. Instructing agent to revise approach.[/]")
                obs_to_send = f"{observation}\n[System Notice: Action halted by circuit breaker after 2 consecutive identical failures. Revise your strategy or conclude with a final answer.]"
            else:
                obs_to_send = observation

            history.append({"role": "assistant", "content": response})
            history.append({"role": "user", "content": f"Observation: {obs_to_send}"})

        console.print("[warning]Max step limit reached before final answer.[/]")

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON block from markdown."""
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        content = match.group(1) if match else text.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Dispatch tool calls safely."""
        if tool_name == "read_file":
            return self._tool_read_file(args.get("path", ""))
        elif tool_name == "write_file":
            return self._tool_write_file(args.get("path", ""), args.get("content", ""))
        elif tool_name == "run_shell":
            return self._tool_run_shell(args.get("command", ""))
        elif tool_name == "fetch_url":
            return self._tool_fetch_url(args.get("url", ""))
        else:
            return f"Unknown tool: '{tool_name}'."

    def _tool_read_file(self, path_str: str) -> str:
        path = resolve_smart_path(path_str)
        if not path.exists():
            return f"Error: File '{path}' does not exist."
        if path.is_dir():
            return f"Error: '{path}' is a directory, not a file."
        try:
            return path.read_text(encoding="utf-8", errors="replace")[:4000]
        except Exception as exc:
            return f"Error reading file: {exc}"

    def _tool_write_file(self, path_str: str, content: str) -> str:
        path = resolve_smart_path(path_str)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return f"Successfully wrote {len(content)} characters to '{path}'."
        except Exception as exc:
            return f"Error writing file: {exc}"

    def _tool_run_shell(self, command: str) -> str:
        if not command:
            return "Error: Empty command."

        if not self.config.agent_auto_approve_commands:
            confirm = questionary.confirm(
                f"Agent wants to run shell command: '{command}'. Allow?",
                default=False,
                style=QUESTIONARY_STYLE,
            ).ask()
            if not confirm:
                return "Execution denied by user."

        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, creationflags=flags)
            output = res.stdout + ("\nError: " + res.stderr if res.stderr else "")
            return output.strip() or "(Command executed with no output)"
        except Exception as exc:
            return f"Command execution failed: {exc}"

    def _tool_fetch_url(self, url: str) -> str:
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url)
                return res.text[:3000]
        except Exception as exc:
            return f"Error fetching URL: {exc}"


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


def run_agent_menu(config: LocaLLMConfig, client: OllamaClient) -> None:
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


def run_agent_interactive(config: LocaLLMConfig, client: OllamaClient) -> None:
    """Interactive prompt to launch an agent task."""
    if not client.is_connected():
        console.print(f"[danger]Error: Ollama service is not reachable at[/] {config.ollama_host}")
        return

    active_ws = getattr(config, "active_workspace", "default")
    policy = getattr(config, "agent_permission_policy", "ask")
    model_display = (
        "[bold #00d7ff]Auto (Smart Router)[/]"
        if config.default_model.lower() == "auto"
        else f"[bold green]{config.default_model}[/]"
    )
    console.print(
        f"[#aaaaaa]Model:[/] {model_display} "
        f"[#aaaaaa]| Workspace:[/] [bold cyan]{active_ws}[/] "
        f"[#aaaaaa]| Policy:[/] [bold cyan]{policy}[/]\n"
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

    engine = AgentEngine(config, client, model_name=target_model)
    engine.run_task(task.strip())
