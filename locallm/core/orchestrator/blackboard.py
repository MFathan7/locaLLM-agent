"""Shared blackboard state for multi-agent coordination and audit logging."""

from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Any, Dict, List, Optional


@dataclass
class AgentStepLog:
    """Audit log entry capturing individual agent action and state transition."""

    timestamp: str
    agent: str
    action: str
    detail: str
    status: str = "success"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "agent": self.agent,
            "action": self.action,
            "detail": self.detail,
            "status": self.status,
        }


@dataclass
class BlackboardState:
    """Central working memory and shared context across cooperating agents."""

    task: str
    workspace: str = "default"
    plan_steps: List[str] = field(default_factory=list)
    research_findings: List[Dict[str, str]] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    step_logs: List[AgentStepLog] = field(default_factory=list)
    final_answer: Optional[str] = None
    is_completed: bool = False

    def log(self, agent: str, action: str, detail: str, status: str = "success") -> None:
        """Append an audit trail log entry."""
        entry = AgentStepLog(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            agent=agent,
            action=action,
            detail=detail,
            status=status,
        )
        self.step_logs.append(entry)

    def add_finding(self, topic: str, content: str, source: str = "") -> None:
        """Record research finding or knowledge excerpt."""
        self.research_findings.append({
            "topic": topic,
            "content": content,
            "source": source,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

    def record_file_edit(self, file_path: str) -> None:
        """Track modified or created file."""
        if file_path not in self.modified_files:
            self.modified_files.append(file_path)

    def record_test(self, command: str, success: bool, output_summary: str) -> None:
        """Track verification command result."""
        self.test_results.append({
            "command": command,
            "success": success,
            "summary": output_summary,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

    def to_compact_context(self) -> str:
        """Produce a token-efficient summary for subagent prompts."""
        lines = [f"[Overall Objective]: {self.task}"]

        if self.plan_steps:
            lines.append("[Current Execution Plan]:")
            for idx, step in enumerate(self.plan_steps, 1):
                lines.append(f"  {idx}. {step}")

        if self.research_findings:
            lines.append("[Key Research Findings & Facts]:")
            for f in self.research_findings[-4:]:
                src = f" (Source: {f['source']})" if f.get("source") else ""
                lines.append(f"  * {f['topic']}{src}: {f['content'][:300]}")

        if self.modified_files:
            lines.append(f"[Files Touched/Created]: {', '.join(self.modified_files)}")

        if self.test_results:
            lines.append("[Latest Test Results]:")
            for t in self.test_results[-2:]:
                status = "PASS" if t["success"] else "FAIL"
                lines.append(f"  * [{status}] {t['command']} -> {t['summary'][:180]}")

        return "\n".join(lines)

    def to_result_dict(self) -> Dict[str, Any]:
        """Serialize complete state into structured dictionary for API and webhooks."""
        return {
            "task": self.task,
            "workspace": self.workspace,
            "is_completed": self.is_completed,
            "final_answer": self.final_answer or "",
            "modified_files": self.modified_files,
            "research_findings_count": len(self.research_findings),
            "test_results": self.test_results,
            "step_logs": [s.to_dict() for s in self.step_logs],
        }
