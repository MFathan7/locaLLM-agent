"""Specialist agents with role-tailored tool sandboxes and dynamic model assignment."""

import json
from typing import Any, Callable, Dict, List, Optional, Set
from locallm.core.orchestrator.blackboard import BlackboardState
from locallm.core.orchestrator.profiler import get_best_model_for_role


class BaseSpecialistAgent:
    """Base specialist subagent operating within a constrained tool sandbox."""

    def __init__(
        self,
        name: str,
        role: str,
        system_directive: str,
        allowed_tools: Set[str],
        config: Any,
        client: Any,
        preferred_model: Optional[str] = None,
        max_steps: int = 6,
    ):
        self.name = name
        self.role = role
        self.system_directive = system_directive
        self.allowed_tools = allowed_tools
        self.config = config
        self.client = client
        self.max_steps = max_steps
        self.model_name = preferred_model or get_best_model_for_role(role, client, config)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return OpenAI/Ollama schemas filtered to this specialist's sandbox."""
        from locallm.core.tools.base import registry
        schemas = registry.get_schemas("assistant")
        return [
            t for t in schemas
            if isinstance(t, dict) and t.get("function", {}).get("name") in self.allowed_tools
        ]

    def execute(
        self,
        subtask: str,
        blackboard: BlackboardState,
        workspace_name: str = "default",
        on_step_event: Optional[Callable[[str, str, str], None]] = None,
    ) -> str:
        """Run autonomous subtask execution within the specialist sandbox."""
        tools = self.get_tool_schemas()
        context_str = blackboard.to_compact_context()

        ws_snippet = ""
        try:
            from locallm.core.workspace import load_workspace_context
            full_ws = load_workspace_context(workspace_name)
            if full_ws:
                ws_snippet = full_ws[:2500] if len(full_ws) > 2500 else full_ws
        except Exception:
            pass

        system_parts = [
            self.system_directive,
            f"Active Workspace: {workspace_name}",
        ]
        if ws_snippet:
            system_parts.append(f"[Workspace Guidelines & Catalogue]:\n{ws_snippet}")
        system_parts.append(context_str)
        system_parts.append(
            "Directives: Focus strictly on your assigned subtask. Use tools when needed. "
            "Consult workspace skills or files if relevant. When finished or when information is gathered, conclude with a direct summary of results."
        )

        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": "\n\n".join(system_parts),
            },
            {
                "role": "user",
                "content": f"Subtask: {subtask}",
            },
        ]

        step = 0
        final_summary = ""
        blackboard.log(self.name, "start", f"Executing subtask: {subtask}")
        if on_step_event:
            on_step_event(self.name, "start", f"Started subtask: {subtask}")

        while step < self.max_steps:
            step += 1
            if on_step_event:
                on_step_event(self.name, "thinking", f"{self.name} ({self.model_name}) is reasoning & preparing actions (Step {step}/{self.max_steps})...")

            try:
                response = self.client.chat_turn(
                    model=self.model_name,
                    messages=messages,
                    tools=tools,
                    temperature=0.2,
                )
            except Exception as exc:
                err_msg = f"Inference error in {self.name}: {exc}"
                blackboard.log(self.name, "error", err_msg, status="error")
                if on_step_event:
                    on_step_event(self.name, "error", err_msg)
                return err_msg

            tool_calls = response.get("tool_calls") or []
            content = response.get("content", "") or ""

            if not tool_calls and content:
                from locallm.core.tools import extract_fallback_tool_calls
                recovered = extract_fallback_tool_calls(content, self.allowed_tools)
                if recovered:
                    tool_calls = recovered

            if not tool_calls:
                final_summary = content
                if on_step_event:
                    summary_first = final_summary.strip().split("\n")[0] if final_summary else "Concluded"
                    on_step_event(self.name, "done", f"Subtask completed: {summary_first[:90]}")
                break

            # Execute tool calls
            messages.append(response)
            for tc in tool_calls:
                fn_info = tc.get("function", {})
                fn_name = fn_info.get("name", "")
                raw_args = fn_info.get("arguments", {})

                if isinstance(raw_args, str):
                    try:
                        fn_args = json.loads(raw_args)
                    except Exception:
                        fn_args = {}
                else:
                    fn_args = raw_args or {}

                if fn_name not in self.allowed_tools:
                    obs = f"Access denied: {fn_name} is outside {self.name} capabilities."
                    if on_step_event:
                        on_step_event(self.name, "error", obs)
                else:
                    detail = fn_args.get("path") or fn_args.get("command") or fn_args.get("query") or fn_args.get("target_path") or ""
                    detail_str = f" [cyan]{detail}[/]" if detail else ""
                    if on_step_event:
                        on_step_event(self.name, "tool_start", f"Calling tool {fn_name}{detail_str}...")
                    from locallm.core.tools import execute_tool
                    obs = execute_tool(
                        name=fn_name,
                        arguments=fn_args,
                        permission_policy="always_allow",
                        interactive=False,
                        workspace_name=workspace_name,
                    )
                    if on_step_event:
                        first_line = obs.strip().split("\n")[0] if obs else "Done"
                        on_step_event(self.name, "tool_done", f"{fn_name} returned: {first_line[:90]}")

                    # Update blackboard metadata
                    if fn_name in ("patch_file", "write_file"):
                        path = fn_args.get("path") or fn_args.get("target_path") or ""
                        if path:
                            blackboard.record_file_edit(path)
                    elif fn_name in ("search_web", "fetch_web", "search_knowledge"):
                        q = fn_args.get("query") or fn_args.get("url") or subtask
                        blackboard.add_finding(topic=q, content=obs[:400], source=fn_name)
                    elif fn_name == "execute_command":
                        cmd = fn_args.get("command", "")
                        is_ok = not ("error" in obs.lower() or "failed" in obs.lower())
                        blackboard.record_test(cmd, is_ok, obs[:200])

                blackboard.log(self.name, fn_name, f"Args: {fn_args} -> Result: {obs[:120]}")

                messages.append({
                    "role": "tool",
                    "content": obs,
                    "tool_call_id": tc.get("id", f"call_{fn_name}_{step}"),
                })

        if not final_summary and content:
            final_summary = content

        blackboard.log(self.name, "finish", f"Completed: {final_summary[:160]}")
        return final_summary or f"{self.name} concluded subtask."


class ResearchSpecialist(BaseSpecialistAgent):
    """Specialist focused on information gathering, web retrieval, and RAG knowledge search."""

    def __init__(self, config: Any, client: Any, preferred_model: Optional[str] = None):
        super().__init__(
            name="ResearchAgent",
            role="researcher",
            system_directive=(
                "You are the Research Specialist Agent. Your mission is to gather verified facts, "
                "architecture documentation, codebase structure, and web references for the team. "
                "Inspect the project directory using list_directory and read_file, inspect local knowledge base documents, and search web sources. "
                "Return concise, grounded insights based on actual files."
            ),
            allowed_tools={"search_web", "fetch_web", "search_knowledge", "read_file", "list_directory"},
            config=config,
            client=client,
            preferred_model=preferred_model,
            max_steps=6,
        )


class CoderSpecialist(BaseSpecialistAgent):
    """Specialist focused on surgical code modifications, syntax checks, and file creation."""

    def __init__(self, config: Any, client: Any, preferred_model: Optional[str] = None):
        super().__init__(
            name="CoderAgent",
            role="coder",
            system_directive=(
                "You are the Coder Specialist Agent. Your mission is high-precision software engineering. "
                "Always call 'read_file' first to inspect exact lines and indentation before modifying existing code. "
                "Always use 'patch_file' over 'write_file' when editing existing code. "
                "Only use 'write_file' when creating brand new files. "
                "Verify file integrity with 'check_syntax'. Write robust, modular code without unnecessary boilerplate."
            ),
            allowed_tools={"patch_file", "write_file", "check_syntax", "read_file", "list_directory"},
            config=config,
            client=client,
            preferred_model=preferred_model,
            max_steps=8,
        )


class AuditorSpecialist(BaseSpecialistAgent):
    """Specialist focused on command execution, system verification, and test diagnostics."""

    def __init__(self, config: Any, client: Any, preferred_model: Optional[str] = None):
        super().__init__(
            name="AuditorAgent",
            role="auditor",
            system_directive=(
                "You are the Auditor & Test Specialist Agent. Your mission is environment verification, "
                "running shell commands/tests safely, inspecting directories, and diagnosing errors objectively."
            ),
            allowed_tools={"execute_command", "list_directory", "resolve_path", "check_syntax", "read_file"},
            config=config,
            client=client,
            preferred_model=preferred_model,
            max_steps=6,
        )
