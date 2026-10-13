"""Supervisor orchestrator coordinating specialist agents via shared blackboard state."""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from locallm.core.orchestrator.blackboard import BlackboardState
from locallm.core.orchestrator.profiler import get_best_model_for_role
from locallm.core.orchestrator.specialists import (
    AuditorSpecialist,
    CoderSpecialist,
    ResearchSpecialist,
)
from locallm.core.workspace import load_workspace_context


class SupervisorOrchestrator:
    """Hierarchical multi-agent supervisor coordinating task planning and subagent execution."""

    def __init__(
        self,
        config: Any,
        client: Any,
        supervisor_model: Optional[str] = None,
        max_orchestration_turns: int = 8,
    ):
        self.config = config
        self.client = client
        self.max_turns = max_orchestration_turns
        self.supervisor_model = supervisor_model or get_best_model_for_role("supervisor", client, config)

        self.researcher = ResearchSpecialist(config, client)
        self.coder = CoderSpecialist(config, client)
        self.auditor = AuditorSpecialist(config, client)

    def _get_supervisor_tools(self) -> List[Dict[str, Any]]:
        """Define delegation tools for the supervisor to dispatch work to specialists."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_researcher",
                    "description": "Delegate research, documentation lookup, or web searching to ResearchAgent.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subtask": {
                                "type": "string",
                                "description": "Specific research question, library info, or documentation to gather.",
                            },
                        },
                        "required": ["subtask"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_coder",
                    "description": "Delegate surgical code patching, file creation, or code inspection to CoderAgent.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subtask": {
                                "type": "string",
                                "description": "Specific coding, patching, refactoring, or file creation objective.",
                            },
                        },
                        "required": ["subtask"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_auditor",
                    "description": "Delegate shell verification commands, test runs, or diagnostic audits to AuditorAgent.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subtask": {
                                "type": "string",
                                "description": "Verification command or diagnostic check to run (e.g. pytest, curl, dir inspection).",
                            },
                        },
                        "required": ["subtask"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "complete_goal",
                    "description": "Declare the overall task accomplished and provide the final comprehensive summary.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "Detailed final answer and outcome summary for the user.",
                            },
                        },
                        "required": ["summary"],
                    },
                },
            },
        ]

    def run(
        self,
        task: str,
        workspace_name: str = "default",
        on_event: Optional[Callable[[str, str, str], None]] = None,
        agent_workspaces: Optional[dict[str, str]] = None,
    ) -> BlackboardState:
        """Execute task through hierarchical multi-agent coordination."""
        agent_ws = agent_workspaces or {}
        supervisor_ws = agent_ws.get("supervisor") or workspace_name
        researcher_ws = agent_ws.get("researcher") or agent_ws.get("research") or workspace_name
        coder_ws = agent_ws.get("coder") or workspace_name
        auditor_ws = agent_ws.get("auditor") or workspace_name

        blackboard = BlackboardState(task=task, workspace=supervisor_ws)
        blackboard.log("Supervisor", "init", f"Initiating task with model: {self.supervisor_model} in workspace: {supervisor_ws}")

        ws_context = ""
        try:
            ws_context = load_workspace_context(workspace_name)
        except Exception:
            pass

        if on_event:
            on_event("Supervisor", "start", f"Task: {task}")
            on_event(
                "Supervisor",
                "team",
                f"Team: Researcher ({self.researcher.model_name}) | "
                f"Coder ({self.coder.model_name}) | "
                f"Auditor ({self.auditor.model_name})",
            )

        cwd = Path.cwd()
        cwd_files = []
        try:
            cwd_files = [p.name for p in cwd.iterdir() if not p.name.startswith(".")]
        except Exception:
            pass
        files_summary = ", ".join(sorted(cwd_files)[:40]) if cwd_files else "(no local files found or empty directory)"

        system_instruction = (
            "You are the Multi-Agent Supervisor Orchestrator.\n"
            "Your objective is to lead a team of specialist local AI agents to achieve the user's goal.\n\n"
            f"Supervisor Model: {self.supervisor_model}\n"
            f"Active Workspace: {workspace_name}\n"
            f"Project Working Directory: {cwd}\n"
            f"Existing Project Files: {files_summary}\n\n"
            "Specialist Team:\n"
            f"- ResearchAgent ({self.researcher.model_name}): Inspect project directory, document indexing, web references, facts retrieval.\n"
            f"- CoderAgent ({self.coder.model_name}): Surgical code edits (patch_file), writing files, syntax checks.\n"
            f"- AuditorAgent ({self.auditor.model_name}): Command executions, test verification, system audits.\n\n"
            "Directives:\n"
            "1. Deconstruct the user objective into targeted subtasks.\n"
            "2. Ground your planning on the actual 'Existing Project Files' listed above. Do not guess nonexistent files.\n"
            "3. Dispatch subtasks to the appropriate specialist using your delegation tools.\n"
            "4. Do NOT do manual coding or shell execution yourself; always delegate to your specialists.\n"
            "5. Review specialist outputs. When sufficient observations are gathered, or when asked for a plan/answer, invoke 'complete_goal' with your comprehensive summary."
        )

        if ws_context:
            system_instruction += f"\n\n{ws_context}"

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Task: {task}"},
        ]

        tools = self._get_supervisor_tools()
        turn = 0
        nudge_sent = False

        while turn < self.max_turns and not blackboard.is_completed:
            turn += 1
            if turn >= self.max_turns - 2 and not nudge_sent:
                nudge_sent = True
                messages.append({
                    "role": "user",
                    "content": (
                        "[System Notice: Turn budget is almost exhausted. Synthesize your findings and "
                        "invoke 'complete_goal' with your comprehensive final answer, plan, or recommendations for the user.]"
                    ),
                })
            if on_event:
                on_event("Supervisor", "planning", f"Supervisor ({self.supervisor_model}) is planning mission strategy (Turn {turn}/{self.max_turns})...")

            try:
                response = self.client.chat_turn(
                    model=self.supervisor_model,
                    messages=messages,
                    tools=tools,
                    temperature=0.2,
                )
            except Exception as exc:
                err_msg = f"Supervisor inference error: {exc}"
                blackboard.log("Supervisor", "error", err_msg, status="error")
                blackboard.final_answer = err_msg
                if on_event:
                    on_event("Supervisor", "error", err_msg)
                break

            tool_calls = response.get("tool_calls") or []
            content = response.get("content", "") or ""

            if not tool_calls and content:
                from locallm.core.tools import extract_fallback_tool_calls
                sup_tool_names = {"delegate_to_researcher", "delegate_to_coder", "delegate_to_auditor", "complete_goal"}
                recovered = extract_fallback_tool_calls(content, sup_tool_names)
                if recovered:
                    tool_calls = recovered

            if not tool_calls:
                # Supervisor replied directly without calling tools
                blackboard.final_answer = content
                blackboard.is_completed = True
                blackboard.log("Supervisor", "complete", "Concluded with direct summary.")
                if on_event:
                    on_event("Supervisor", "complete", "Mission goal concluded.")
                break

            messages.append(response)

            for tc in tool_calls:
                fn_info = tc.get("function", {})
                fn_name = fn_info.get("name", "")
                raw_args = fn_info.get("arguments", {})

                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {}
                else:
                    args = raw_args or {}

                if fn_name == "complete_goal":
                    summary = args.get("summary", content)
                    blackboard.final_answer = summary
                    blackboard.is_completed = True
                    blackboard.log("Supervisor", "complete_goal", summary[:160])
                    if on_event:
                        on_event("Supervisor", "complete", "Mission goal achieved.")
                    messages.append({
                        "role": "tool",
                        "content": "Goal finalized successfully.",
                        "tool_call_id": tc.get("id", f"call_complete_{turn}"),
                    })
                    break

                elif fn_name == "delegate_to_researcher":
                    subtask = args.get("subtask", "")
                    if on_event:
                        on_event("Supervisor", "delegate", f"Delegating to ResearchAgent ({self.researcher.model_name}) [ws: {researcher_ws}]: {subtask}")
                    res = self.researcher.execute(
                        subtask=subtask,
                        blackboard=blackboard,
                        workspace_name=researcher_ws,
                        on_step_event=on_event,
                    )
                    if on_event:
                        first_line = res.strip().split("\n")[0] if res else "Completed"
                        on_event("Supervisor", "subtask_done", f"ResearchAgent concluded: {first_line[:90]}")
                    messages.append({
                        "role": "tool",
                        "content": f"[ResearchAgent Result]:\n{res}",
                        "tool_call_id": tc.get("id", f"call_res_{turn}"),
                    })

                elif fn_name == "delegate_to_coder":
                    subtask = args.get("subtask", "")
                    if on_event:
                        on_event("Supervisor", "delegate", f"Delegating to CoderAgent ({self.coder.model_name}) [ws: {coder_ws}]: {subtask}")
                    res = self.coder.execute(
                        subtask=subtask,
                        blackboard=blackboard,
                        workspace_name=coder_ws,
                        on_step_event=on_event,
                    )
                    if on_event:
                        first_line = res.strip().split("\n")[0] if res else "Completed"
                        on_event("Supervisor", "subtask_done", f"CoderAgent concluded: {first_line[:90]}")
                    messages.append({
                        "role": "tool",
                        "content": f"[CoderAgent Result]:\n{res}",
                        "tool_call_id": tc.get("id", f"call_coder_{turn}"),
                    })

                elif fn_name == "delegate_to_auditor":
                    subtask = args.get("subtask", "")
                    if on_event:
                        on_event("Supervisor", "delegate", f"Delegating to AuditorAgent ({self.auditor.model_name}) [ws: {auditor_ws}]: {subtask}")
                    res = self.auditor.execute(
                        subtask=subtask,
                        blackboard=blackboard,
                        workspace_name=auditor_ws,
                        on_step_event=on_event,
                    )
                    if on_event:
                        first_line = res.strip().split("\n")[0] if res else "Completed"
                        on_event("Supervisor", "subtask_done", f"AuditorAgent concluded: {first_line[:90]}")
                    messages.append({
                        "role": "tool",
                        "content": f"[AuditorAgent Result]:\n{res}",
                        "tool_call_id": tc.get("id", f"call_auditor_{turn}"),
                    })

        if not blackboard.final_answer:
            if on_event:
                on_event("Supervisor", "planning", f"Supervisor ({self.supervisor_model}) is synthesizing final report...")
            synth_messages = list(messages) + [
                {
                    "role": "user",
                    "content": (
                        f"The execution turns have concluded. Based on the objective ('{task}') and all findings, "
                        f"file edits, and observations gathered during this mission, synthesize your final comprehensive "
                        f"answer, analysis, and plan for the user now."
                    ),
                }
            ]
            try:
                synth_res = self.client.chat_turn(
                    model=self.supervisor_model,
                    messages=synth_messages,
                    temperature=0.3,
                )
                final_synth = synth_res.get("content", "").strip() if isinstance(synth_res, dict) else ""
                if final_synth:
                    blackboard.final_answer = final_synth
            except Exception:
                pass

            if not blackboard.final_answer:
                findings_summary = "\n".join([f"- {f.get('topic')}: {f.get('content')[:120]}" for f in blackboard.research_findings[:5]])
                blackboard.final_answer = (
                    f"Multi-agent mission concluded after {turn} turns.\n"
                    f"Findings gathered:\n{findings_summary or 'No specific findings recorded.'}"
                )
            blackboard.is_completed = True

        return blackboard
