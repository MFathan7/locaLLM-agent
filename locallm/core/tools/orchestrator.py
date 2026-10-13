"""Multi-agent team dispatch tool for interactive chat assistants and integrations."""

from typing import Any, Dict, Optional
from locallm.config import load_config
from locallm.core.tools.base import tool


def dispatch_agent_team_fn(
    task: str,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Dispatch specialized multi-agent team to autonomously execute a composite goal."""
    clean_task = task.strip()
    if not clean_task:
        return "Error: Agent task cannot be empty."

    from locallm.core.openai_client import get_inference_client
    from locallm.core.orchestrator.supervisor import SupervisorOrchestrator

    ws_name = (context or {}).get("workspace_name")
    cfg = load_config()
    client = get_inference_client(cfg)
    target_ws = ws_name or getattr(cfg, "active_workspace", "default")

    orchestrator = SupervisorOrchestrator(cfg, client)
    blackboard = orchestrator.run(task=clean_task, workspace_name=target_ws)

    summary_parts = [
        f"Multi-Agent Team Execution Report for '{clean_task}':",
        f"Outcome: {blackboard.final_answer or 'Task completed.'}",
    ]

    if blackboard.modified_files:
        summary_parts.append(f"Files Modified/Created: {', '.join(blackboard.modified_files)}")
    if blackboard.test_results:
        summary_parts.append(f"Verification Commands Run: {len(blackboard.test_results)}")

    return "\n\n".join(summary_parts)


# Register tool
tool(
    name="dispatch_agent_team",
    description="Dispatch a specialized local multi-agent team (Supervisor, Researcher, Coder, and Auditor) to autonomously execute a complex multi-step objective, research question, or coding task. Returns full findings, modified files, and summary.",
    parameters={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Clear goal, programming requirement, or research objective to assign to the multi-agent team.",
            },
        },
        "required": ["task"],
    },
    is_mutating=True,
    is_privileged=False,
    categories={"assistant", "telegram", "whatsapp"},
)(dispatch_agent_team_fn)
