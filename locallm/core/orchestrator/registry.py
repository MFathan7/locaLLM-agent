"""Persistent Workflow Registry and Execution History Manager for locaLLM.

Manages persistent JSON workflow definitions, active background state (isActive),
CRUD lifecycle, and full observability execution history on the local filesystem.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

# Base directories for workflows and execution history
def get_workflows_base_dir() -> Path:
    """Return base directory for workflow definitions (~/.locallm/workflows)."""
    base = Path.home() / ".locallm" / "workflows"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_definitions_dir() -> Path:
    """Return directory for stored workflow JSON files."""
    d = get_workflows_base_dir() / "definitions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_history_dir() -> Path:
    """Return directory for execution history logs."""
    h = get_workflows_base_dir() / "history"
    h.mkdir(parents=True, exist_ok=True)
    return h


class WorkflowRegistry:
    """Thread-safe persistent registry for visual agent workflows and telemetry history."""

    _instance: Optional["WorkflowRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "WorkflowRegistry":
        if "base_dir" in kwargs or "definitions_dir" in kwargs or "history_dir" in kwargs:
            instance = super().__new__(cls)
            instance._initialized = False
            return instance
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(
        self,
        base_dir: Optional[Union[str, Path]] = None,
        definitions_dir: Optional[Union[str, Path]] = None,
        history_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        if getattr(self, "_initialized", False) and base_dir is None and definitions_dir is None:
            return

        if base_dir:
            base_p = Path(base_dir)
            self.definitions_dir = base_p / "definitions"
            self.history_dir = base_p / "history"
        else:
            self.definitions_dir = Path(definitions_dir) if definitions_dir else get_definitions_dir()
            self.history_dir = Path(history_dir) if history_dir else get_history_dir()

        self.definitions_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._rw_lock = threading.Lock()
        self._execution_ring: List[Dict[str, Any]] = []
        self._max_ring_size = 200
        self._seed_default_presets_if_empty()
        self._load_recent_history_into_ring()
        self._initialized = True

    def _seed_default_presets_if_empty(self) -> None:
        """Seed default workflow presets if definitions directory is currently empty."""
        existing = list(self.definitions_dir.glob("*.json"))
        if existing:
            return

        default_presets = [
            {
                "id": "fullstack-code-audit",
                "name": "Full-Stack Code Audit & Auto-Refactor",
                "description": "Autonomous repository audit with task decomposition, Coder Specialist tooling, Critic verification, and Quality Gate revision loops.",
                "isActive": False,
                "version": "1.0.0",
                "lanes": [
                    {"id": "ui", "num": "01", "label": "User Interface Sequence", "color": "blue", "x": 30, "y": 70, "width": 1750, "height": 135},
                    {"id": "agent", "num": "02", "label": "Agent Runtime Sequence", "color": "blue", "x": 30, "y": 225, "width": 1750, "height": 145},
                    {"id": "policy", "num": "03", "label": "Policy & Guardrail Sequence", "color": "red", "x": 30, "y": 390, "width": 1750, "height": 135},
                    {"id": "tools", "num": "04", "label": "Tool Execution Sequence", "color": "yellow", "x": 30, "y": 545, "width": 1750, "height": 145},
                    {"id": "evidence", "num": "05", "label": "Evidence & Context Sequence", "color": "blue", "x": 30, "y": 710, "width": 1750, "height": 135}
                ],
                "nodes": [
                    {
                        "id": "audit-intake",
                        "lane": "ui",
                        "category": "triggers",
                        "type": "frontend",
                        "title": "User Objective Input",
                        "subtitle": "Repository target & audit directives",
                        "tag": "intake",
                        "x": 60,
                        "y": 105,
                        "status": "idle",
                        "properties": {
                            "common": {"displayName": "User Objective Input", "description": "Repository target & audit directives", "continueOnError": False, "timeoutSeconds": 30},
                            "inputs": {"query": "Perform full-stack audit across backend modules and test suite. Detect failing assertions, memory bottlenecks, and syntax regressions, patch affected source files, and verify 100% test coverage with pytest.", "workspace": "default"},
                            "options": {"sourceType": "manual"},
                            "output": {"outputVariable": "out_user_objective"}
                        }
                    },
                    {
                        "id": "audit-decomposer",
                        "lane": "agent",
                        "category": "orchestration",
                        "type": "backend",
                        "title": "Task Decomposer (Planner)",
                        "subtitle": "Splits audit into ordered task queue",
                        "tag": "task-decomposer",
                        "x": 320,
                        "y": 265,
                        "status": "idle",
                        "properties": {
                            "common": {"displayName": "Task Decomposer (Planner)", "description": "Splits audit into ordered task queue", "continueOnError": False, "timeoutSeconds": 60},
                            "inputs": {"objective": "{{out_user_objective}}"},
                            "options": {"max_subtasks": 4, "strategy": "hierarchical"},
                            "output": {"outputVariable": "out_task_queue"}
                        }
                    },
                    {
                        "id": "audit-supervisor",
                        "lane": "agent",
                        "category": "orchestration",
                        "type": "backend",
                        "title": "Agent Coordinator (Supervisor)",
                        "subtitle": "Synthesizes context & delegates subtasks",
                        "tag": "orchestrator",
                        "x": 600,
                        "y": 265,
                        "status": "idle",
                        "properties": {
                            "common": {"displayName": "Agent Coordinator (Supervisor)", "description": "Synthesizes context & delegates subtasks", "continueOnError": False, "timeoutSeconds": 60},
                            "inputs": {"systemPrompt": "Coordinate and direct specialist execution for code audit and patching.", "directive": "Review test failure logs and coordinate coder and critic."},
                            "options": {"parameterMode": "auto", "temperature": 0.2},
                            "output": {"outputVariable": "out_supervisor_directive"}
                        }
                    },
                    {
                        "id": "audit-coder",
                        "lane": "agent",
                        "category": "specialists",
                        "type": "backend",
                        "title": "Coder Specialist",
                        "subtitle": "Authors code patches & fixes syntax",
                        "tag": "coder",
                        "x": 880,
                        "y": 265,
                        "status": "idle",
                        "properties": {
                            "common": {"displayName": "Coder Specialist", "description": "Authors code patches & fixes syntax", "continueOnError": False, "timeoutSeconds": 120},
                            "inputs": {"taskPrompt": "Implement fixes for detected code regressions and generate diff patch.", "filePath": "docs/patch_revision.diff"},
                            "options": {"parameterMode": "auto", "model": "auto"},
                            "output": {"outputVariable": "out_code_diff"}
                        }
                    },
                    {
                        "id": "audit-critic",
                        "lane": "agent",
                        "category": "specialists",
                        "type": "backend",
                        "title": "Critic / QA Auditor",
                        "subtitle": "Evaluates diff against quality criteria",
                        "tag": "critic",
                        "x": 1160,
                        "y": 265,
                        "status": "idle",
                        "properties": {
                            "common": {"displayName": "Critic / QA Auditor", "description": "Evaluates diff against quality criteria", "continueOnError": False, "timeoutSeconds": 60},
                            "inputs": {"reviewTarget": "{{out_code_diff}}"},
                            "options": {"passThreshold": 80},
                            "output": {"outputVariable": "out_qa_verdict"}
                        }
                    },
                    {
                        "id": "audit-quality-gate",
                        "lane": "policy",
                        "category": "flow_control",
                        "type": "security",
                        "title": "Quality Gate (Decision Branch)",
                        "subtitle": "Evaluates QA score & routes pass vs retry",
                        "tag": "quality-gate",
                        "x": 1360,
                        "y": 425,
                        "status": "idle",
                        "properties": {
                            "common": {"displayName": "Quality Gate (Decision Branch)", "description": "Evaluates QA score & routes pass vs retry", "continueOnError": False, "timeoutSeconds": 10},
                            "inputs": {"conditionExpression": "{{out_qa_verdict.score}} >= 80"},
                            "options": {"maxRetries": 2},
                            "output": {"outputVariable": "out_gate_status"}
                        }
                    },
                    {
                        "id": "audit-exporter",
                        "lane": "ui",
                        "category": "outputs",
                        "type": "frontend",
                        "title": "Document Exporter",
                        "subtitle": "Generates verified audit report deliverable",
                        "tag": "doc-exporter",
                        "x": 1600,
                        "y": 105,
                        "status": "idle",
                        "properties": {
                            "common": {"displayName": "Document Exporter", "description": "Generates verified audit report deliverable", "continueOnError": False, "timeoutSeconds": 30},
                            "inputs": {"filePath": "docs/code_audit_report.md"},
                            "options": {"exportFormat": "markdown", "notifyUser": True},
                            "output": {"outputVariable": "out_exported_report"}
                        }
                    }
                ],
                "edges": [
                    {"id": "e1", "from": "audit-intake", "to": "audit-decomposer", "kind": "main"},
                    {"id": "e2", "from": "audit-decomposer", "to": "audit-supervisor", "kind": "main"},
                    {"id": "e3", "from": "audit-supervisor", "to": "audit-coder", "kind": "main"},
                    {"id": "e4", "from": "audit-coder", "to": "audit-critic", "kind": "main"},
                    {"id": "e5", "from": "audit-critic", "to": "audit-quality-gate", "kind": "main"},
                    {"id": "e6", "from": "audit-quality-gate", "to": "audit-supervisor", "kind": "main", "conditionBranch": "loop", "label": "Revise Loop"},
                    {"id": "e7", "from": "audit-quality-gate", "to": "audit-exporter", "kind": "main", "conditionBranch": "pass", "label": "Approved"}
                ],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": "telegram-incident-responder",
                "name": "Live Messaging Incident Responder",
                "description": "Background messaging responder: listens for inbound alerts from Telegram/WhatsApp, runs diagnostic tools, and dispatches real replies.",
                "isActive": False,
                "version": "1.0.0",
                "lanes": [
                    {"id": "ui", "num": "01", "label": "User Interface Sequence", "color": "blue", "x": 30, "y": 70, "width": 1750, "height": 135},
                    {"id": "agent", "num": "02", "label": "Agent Runtime Sequence", "color": "blue", "x": 30, "y": 225, "width": 1750, "height": 145},
                    {"id": "policy", "num": "03", "label": "Policy & Guardrail Sequence", "color": "red", "x": 30, "y": 390, "width": 1750, "height": 135},
                    {"id": "tools", "num": "04", "label": "Tool Execution Sequence", "color": "yellow", "x": 30, "y": 545, "width": 1750, "height": 145},
                    {"id": "evidence", "num": "05", "label": "Evidence & Context Sequence", "color": "blue", "x": 30, "y": 710, "width": 1750, "height": 135}
                ],
                "nodes": [
                    {
                        "id": "msg-trigger-node",
                        "lane": "ui",
                        "category": "triggers",
                        "type": "frontend",
                        "title": "Messaging Inbound Trigger",
                        "subtitle": "Listens for live Telegram/WhatsApp chats",
                        "tag": "messaging-trigger",
                        "x": 60,
                        "y": 105,
                        "status": "idle",
                        "properties": {
                            "common": {"displayName": "Messaging Inbound Trigger", "description": "Listens for live chats", "continueOnError": False, "timeoutSeconds": 30},
                            "inputs": {"query": "Check system status and disk health"},
                            "options": {"platform": "telegram"},
                            "output": {"outputVariable": "out_inbound_chat"}
                        }
                    },
                    {
                        "id": "msg-supervisor-node",
                        "lane": "agent",
                        "category": "orchestration",
                        "type": "backend",
                        "title": "Incident Coordinator",
                        "subtitle": "Plans diagnostic commands",
                        "tag": "orchestrator",
                        "x": 360,
                        "y": 265,
                        "status": "idle",
                        "properties": {
                            "common": {"displayName": "Incident Coordinator", "description": "Plans diagnostic commands", "continueOnError": False, "timeoutSeconds": 60},
                            "inputs": {"systemPrompt": "Inspect system health based on user inquiry."},
                            "options": {"parameterMode": "auto"},
                            "output": {"outputVariable": "out_supervisor_directive"}
                        }
                    },
                    {
                        "id": "msg-shell-node",
                        "lane": "tools",
                        "category": "tools",
                        "type": "backend",
                        "title": "Shell Runner (Diagnostics)",
                        "subtitle": "Runs real terminal health checks",
                        "tag": "subprocess",
                        "x": 660,
                        "y": 580,
                        "status": "idle",
                        "properties": {
                            "common": {"displayName": "Shell Runner", "description": "Runs terminal health checks", "continueOnError": True, "timeoutSeconds": 30},
                            "inputs": {"shellCommand": "df -h && uptime"},
                            "options": {"parameterMode": "auto"},
                            "output": {"outputVariable": "out_shell_diagnostics"}
                        }
                    },
                    {
                        "id": "msg-dispatcher-node",
                        "lane": "ui",
                        "category": "outputs",
                        "type": "frontend",
                        "title": "Messaging Dispatcher",
                        "subtitle": "Dispatches live response to Telegram/WhatsApp",
                        "tag": "messaging-dispatcher",
                        "x": 980,
                        "y": 105,
                        "status": "idle",
                        "properties": {
                            "common": {"displayName": "Messaging Dispatcher", "description": "Dispatches live response", "continueOnError": False, "timeoutSeconds": 30},
                            "inputs": {"messageTemplate": "System Diagnostics Report:\n\n{{out_shell_diagnostics}}"},
                            "options": {"channel": "telegram"},
                            "output": {"outputVariable": "out_delivery_status"}
                        }
                    }
                ],
                "edges": [
                    {"id": "e_msg1", "from": "msg-trigger-node", "to": "msg-supervisor-node", "kind": "main"},
                    {"id": "e_msg2", "from": "msg-supervisor-node", "to": "msg-shell-node", "kind": "main"},
                    {"id": "e_msg3", "from": "msg-shell-node", "to": "msg-dispatcher-node", "kind": "main"}
                ],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]

        for p in default_presets:
            p_file = self.definitions_dir / f"{p['id']}.json"
            try:
                p_file.write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

    def _load_recent_history_into_ring(self) -> None:
        """Load the most recent execution history files into memory ring buffer on startup."""
        try:
            files = sorted(self.history_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
            for f in files[:self._max_ring_size]:
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    self._execution_ring.append(data)
                except Exception:
                    pass
        except Exception:
            pass

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflow definitions with metadata summaries."""
        with self._rw_lock:
            results = []
            for f in sorted(self.definitions_dir.glob("*.json")):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    results.append({
                        "id": data.get("id") or f.stem,
                        "name": data.get("name") or data.get("title") or f.stem,
                        "title": data.get("name") or data.get("title") or f.stem,
                        "description": data.get("description", ""),
                        "isActive": bool(data.get("isActive", False)),
                        "nodes_count": len(data.get("nodes", [])),
                        "edges_count": len(data.get("edges", [])),
                        "created_at": data.get("created_at", ""),
                        "updated_at": data.get("updated_at", ""),
                        "version": data.get("version", "1.0.0"),
                    })
                except Exception:
                    continue
            return results

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full workflow definition by ID."""
        clean_id = Path(workflow_id.strip()).stem
        w_file = self.definitions_dir / f"{clean_id}.json"
        if not w_file.exists():
            return None
        with self._rw_lock:
            try:
                return json.loads(w_file.read_text(encoding="utf-8"))
            except Exception:
                return None

    def save_workflow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a workflow definition permanently on disk."""
        workflow_id = str(payload.get("id") or payload.get("workflow_id") or uuid.uuid4().hex[:12]).strip()
        clean_id = "".join(c if (c.isalnum() or c in "-_") else "-" for c in workflow_id).lower()
        if not clean_id:
            clean_id = f"workflow-{uuid.uuid4().hex[:8]}"

        w_file = self.definitions_dir / f"{clean_id}.json"
        now_iso = datetime.now().isoformat()

        # Preserve creation date if updating existing
        existing_created_at = now_iso
        existing_is_active = False
        if w_file.exists():
            try:
                old = json.loads(w_file.read_text(encoding="utf-8"))
                existing_created_at = old.get("created_at", now_iso)
                existing_is_active = old.get("isActive", False)
            except Exception:
                pass

        title = str(payload.get("name") or payload.get("title") or clean_id).strip()
        description = str(payload.get("description") or "").strip()
        is_active = payload.get("isActive")
        if is_active is None:
            is_active = existing_is_active
        else:
            is_active = bool(is_active)

        nodes = payload.get("nodes") or []
        edges = payload.get("edges") or []
        lanes = payload.get("lanes") or []

        full_doc = {
            "id": clean_id,
            "name": title,
            "title": title,
            "description": description,
            "isActive": is_active,
            "version": str(payload.get("version", "1.0.0")),
            "lanes": lanes,
            "nodes": nodes,
            "edges": edges,
            "created_at": existing_created_at,
            "updated_at": now_iso,
        }

        with self._rw_lock:
            w_file.write_text(json.dumps(full_doc, indent=2, ensure_ascii=False), encoding="utf-8")
            if is_active:
                for other_file in self.definitions_dir.glob("*.json"):
                    if other_file.stem != clean_id:
                        try:
                            other_data = json.loads(other_file.read_text(encoding="utf-8"))
                            if other_data.get("isActive"):
                                other_data["isActive"] = False
                                other_data["updated_at"] = now_iso
                                other_file.write_text(json.dumps(other_data, indent=2, ensure_ascii=False), encoding="utf-8")
                        except Exception:
                            pass

        return full_doc

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete workflow definition permanently from disk."""
        clean_id = Path(workflow_id.strip()).stem
        w_file = self.definitions_dir / f"{clean_id}.json"
        if not w_file.exists():
            return False
        with self._rw_lock:
            try:
                w_file.unlink()
                return True
            except Exception:
                return False

    def toggle_active(self, workflow_id: str, target_state: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        """Toggle or set the isActive boolean state for background triggers."""
        clean_id = Path(workflow_id.strip()).stem
        w_file = self.definitions_dir / f"{clean_id}.json"
        if not w_file.exists():
            return None

        with self._rw_lock:
            try:
                data = json.loads(w_file.read_text(encoding="utf-8"))
                current = bool(data.get("isActive", False))
                new_state = (not current) if target_state is None else bool(target_state)
                data["isActive"] = new_state
                data["updated_at"] = datetime.now().isoformat()
                w_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

                # Exclusive Live Mode: Ensure only ONE workflow is active at a time to prevent local hardware overload
                if new_state:
                    for other_file in self.definitions_dir.glob("*.json"):
                        if other_file.stem != clean_id:
                            try:
                                other_data = json.loads(other_file.read_text(encoding="utf-8"))
                                if other_data.get("isActive"):
                                    other_data["isActive"] = False
                                    other_data["updated_at"] = datetime.now().isoformat()
                                    other_file.write_text(json.dumps(other_data, indent=2, ensure_ascii=False), encoding="utf-8")
                            except Exception:
                                pass

                return data
            except Exception:
                return None

    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Return all workflow definitions that are marked isActive == True."""
        active = []
        with self._rw_lock:
            for f in self.definitions_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if bool(data.get("isActive", False)):
                        active.append(data)
                except Exception:
                    continue
        return active

    def record_execution(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Record an execution history item to disk and memory ring buffer."""
        run_id = record.get("run_id") or str(uuid.uuid4())
        record["run_id"] = run_id
        if "timestamp" not in record:
            record["timestamp"] = datetime.now().isoformat()

        h_file = self.history_dir / f"{run_id}.json"
        with self._rw_lock:
            try:
                h_file.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass
            self._execution_ring.insert(0, record)
            if len(self._execution_ring) > self._max_ring_size:
                self._execution_ring.pop()

        return record

    def list_execution_history(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List execution history records, optionally filtered by workflow_id."""
        with self._rw_lock:
            if not workflow_id:
                return list(self._execution_ring)[:limit]

            filtered = [
                r for r in self._execution_ring
                if str(r.get("workflow_id", "")).strip().lower() == workflow_id.strip().lower()
            ]
            return filtered[:limit]

    def get_execution_record(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get full execution record details by run_id."""
        clean_run = Path(run_id.strip()).stem
        # Check memory first
        with self._rw_lock:
            for r in self._execution_ring:
                if r.get("run_id") == clean_run:
                    return r

        h_file = self.history_dir / f"{clean_run}.json"
        if h_file.exists():
            try:
                return json.loads(h_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    # Convenience aliases
    get_history = list_execution_history
    get_execution = get_execution_record


# Global singleton access
_REGISTRY_INSTANCE: Optional[WorkflowRegistry] = None

def get_workflow_registry() -> WorkflowRegistry:
    """Retrieve the global WorkflowRegistry singleton instance."""
    global _REGISTRY_INSTANCE
    if _REGISTRY_INSTANCE is None:
        _REGISTRY_INSTANCE = WorkflowRegistry()
    return _REGISTRY_INSTANCE
