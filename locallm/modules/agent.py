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
from locallm.ui.theme import QUESTIONARY_STYLE, console

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
  "final_answer": "Detailed answer or summary of actions taken"
}
```

Available tools:
1. `run_shell`: Execute a safe command in the local shell.
   Args: {"command": "powershell or bash command string"}
2. `read_file`: Read contents of a local file.
   Args: {"path": "relative or absolute file path"}
3. `write_file`: Write or overwrite text file.
   Args: {"path": "file path", "content": "content string"}
4. `fetch_url`: Fetch web text content from a URL.
   Args: {"url": "https://..."}

Always provide valid JSON within triple backticks.
"""


class AgentEngine:
    """ReAct execution loop using local Ollama model."""

    def __init__(self, config: LocaLLMConfig, client: OllamaClient):
        self.config = config
        self.client = client
        self.max_steps = 10

    def run_task(self, task_instruction: str) -> None:
        """Execute a task through multi-step reasoning."""
        console.print(Panel(task_instruction, title="[bold cyan]Agent Task[/]", border_style="cyan"))

        ws_context = load_workspace_context(getattr(self.config, "active_workspace", "default"))
        system_content = SYSTEM_AGENT_PROMPT
        if ws_context:
            system_content += f"\n\n{ws_context}"

        history: List[Dict[str, str]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"Task: {task_instruction}"},
        ]

        for step in range(1, self.max_steps + 1):
            from locallm.ui.spinner import thinking_spinner

            try:
                with thinking_spinner(f"Agent is planning step {step}/{self.max_steps}...", style="bold magenta"):
                    response = self.client.chat(
                        model=self.config.default_model,
                        messages=history,
                        temperature=0.2,
                    )
            except Exception as exc:
                console.print(f"[danger]Agent error communicating with model:[/] {exc}")
                return

            action_data = self._extract_json(response)
            if not action_data:
                console.print(Panel(response, title="[dim]Model Note[/]", border_style="dim"))
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
                    title="[bold green]Task Completed[/]",
                    border_style="green",
                ))
                return

            tool_name = action_data.get("tool")
            args = action_data.get("args", {})

            console.print(f"[bold cyan]Action:[/] `{tool_name}` with args: [dim]{json.dumps(args)}[/]")

            # Execute tool
            observation = self._execute_tool(tool_name, args)
            console.print(f"[dim green]Observation:[/] {observation[:180]}..." if len(observation) > 180 else f"[dim green]Observation:[/] {observation}")

            history.append({"role": "assistant", "content": response})
            history.append({"role": "user", "content": f"Observation: {observation}"})

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


def toggle_agent_auto_approve(config: LocaLLMConfig) -> None:
    """Toggle whether agent automatically executes shell commands without confirmation."""
    config.agent_auto_approve_commands = not config.agent_auto_approve_commands
    save_config(config)
    status = "ENABLED" if config.agent_auto_approve_commands else "DISABLED"
    console.print(f"[success]Agent command auto-approval is now: {status}[/]\n")


def run_agent_menu(config: LocaLLMConfig, client: OllamaClient) -> None:
    """Interactive submenu for Autonomous Agent & Automation."""
    while True:
        status_label = "ENABLED" if config.agent_auto_approve_commands else "DISABLED"
        choice = questionary.select(
            "Agent & Automation:",
            choices=[
                "Run Agent Task",
                f"Auto-Approve Shell Commands (Current: {status_label})",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice == "Run Agent Task":
            run_agent_interactive(config, client)
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        elif choice.startswith("Auto-Approve Shell Commands"):
            toggle_agent_auto_approve(config)


def run_agent_interactive(config: LocaLLMConfig, client: OllamaClient) -> None:
    """Interactive prompt to launch an agent task."""
    if not client.is_connected():
        console.print(f"[danger]Error: Ollama service is not reachable at[/] {config.ollama_host}")
        return

    active_ws = getattr(config, "active_workspace", "default")
    console.print(
        f"[#aaaaaa]Model:[/] [bold green]{config.default_model}[/] "
        f"[#aaaaaa]| Workspace:[/] [bold cyan]{active_ws}[/] "
        f"[#aaaaaa]| Auto-approve:[/] {config.agent_auto_approve_commands}\n"
    )

    task = questionary.text(
        "Enter your task or goal for the Agent (leave blank to cancel):",
        style=QUESTIONARY_STYLE,
    ).ask()

    if not task or not task.strip():
        console.print("[#aaaaaa]Task entry cancelled.[/]")
        return

    engine = AgentEngine(config, client)
    engine.run_task(task.strip())
