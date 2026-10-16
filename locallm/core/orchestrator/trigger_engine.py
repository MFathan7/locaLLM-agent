"""Background Trigger Engine for locaLLM Visual Agent Workflows.

Coordinates background execution for active workflows:
1. Schedule Trigger loop (cron / interval checks)
2. Inbound messaging hooks (WhatsApp & Telegram)
3. Dynamic HTTP webhook receiver
"""

from datetime import datetime
import json
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional
import uuid

from locallm.config import LocaLLMConfig, load_config
from locallm.core.orchestrator.registry import get_workflow_registry


def _is_cron_due(cron_expr: str, now: datetime, last_run: Optional[datetime]) -> bool:
    """Evaluate whether a standard cron expression (or alias) is due at `now`."""
    clean_expr = cron_expr.strip().lower()

    # Predefined aliases
    if clean_expr == "@hourly":
        clean_expr = "0 * * * *"
    elif clean_expr == "@daily":
        clean_expr = "0 0 * * *"
    elif clean_expr == "@weekly":
        clean_expr = "0 0 * * 0"

    # Avoid duplicate executions in the exact same minute
    if last_run and last_run.year == now.year and last_run.month == now.month and \
       last_run.day == now.day and last_run.hour == now.hour and last_run.minute == now.minute:
        return False

    parts = clean_expr.split()
    if len(parts) != 5:
        # Fallback interval parsing e.g. "every 10m" or "10m"
        m = re.match(r"(?:every\s+)?(\d+)\s*m(?:in(?:ute)?s?)?", clean_expr)
        if m:
            interval_m = int(m.group(1))
            if not last_run:
                return True
            diff_sec = (now - last_run).total_seconds()
            return diff_sec >= (interval_m * 60)
        return False

    min_part, hr_part, dom_part, mon_part, dow_part = parts

    def match_component(field: str, val: int) -> bool:
        if field == "*":
            return True
        if field.startswith("*/"):
            try:
                step = int(field[2:])
                return val % step == 0
            except Exception:
                return False
        if "," in field:
            return any(match_component(sub, val) for sub in field.split(","))
        if "-" in field:
            try:
                lo, hi = map(int, field.split("-"))
                return lo <= val <= hi
            except Exception:
                return False
        try:
            return int(field) == val
        except Exception:
            return False

    # DOW in Python is 0=Monday..6=Sunday; Cron standard is 0=Sunday..6=Saturday
    cron_dow = (now.weekday() + 1) % 7

    return (
        match_component(min_part, now.minute)
        and match_component(hr_part, now.hour)
        and match_component(dom_part, now.day)
        and match_component(mon_part, now.month)
        and match_component(dow_part, cron_dow)
    )


class WorkflowTriggerEngine:
    """Background engine monitoring active workflows for triggers."""

    _instance: Optional["WorkflowTriggerEngine"] = None
    _lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "WorkflowTriggerEngine":
        if "registry" in kwargs or "config" in kwargs:
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
        config: Optional[LocaLLMConfig] = None,
        client: Optional[Any] = None,
        registry: Optional[Any] = None,
    ) -> None:
        if getattr(self, "_initialized", False) and registry is None:
            return
        self.config = config or load_config()
        self.client = client
        self.registry = registry or get_workflow_registry()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_scheduled_runs: Dict[str, datetime] = {}
        self._execution_lock = threading.Lock()
        self._initialized = True

    def start(self) -> None:
        """Start the background scheduler thread."""
        with self._execution_lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="WorkflowScheduler")
            self._thread.start()

    def stop(self) -> None:
        """Stop the background scheduler loop."""
        with self._execution_lock:
            self._running = False

    def _scheduler_loop(self) -> None:
        """Periodic background evaluation loop for active schedule triggers."""
        while self._running:
            try:
                now = datetime.now()
                active_workflows = self.registry.get_active_workflows()

                for wf in active_workflows:
                    wf_id = wf.get("id") or ""
                    nodes = wf.get("nodes") or []
                    edges = wf.get("edges") or []

                    # Find schedule trigger node
                    sched_node = next(
                        (n for n in nodes if (n.get("tag") or "").lower() == "schedule-trigger" or "schedule" in (n.get("title") or "").lower()),
                        None
                    )
                    if not sched_node:
                        continue

                    props = sched_node.get("resolved_properties") or sched_node.get("properties") or {}
                    inputs = props.get("inputs", {})
                    cfg = sched_node.get("config", {})
                    cron_expr = str(inputs.get("cron") or cfg.get("cron") or "0 2 * * *").strip()

                    last_run = self._last_scheduled_runs.get(wf_id)
                    if _is_cron_due(cron_expr, now, last_run):
                        self._last_scheduled_runs[wf_id] = now
                        threading.Thread(
                            target=self._execute_workflow_async,
                            args=(wf, "schedule", {"scheduled_time": now.isoformat(), "cron": cron_expr}),
                            daemon=True,
                        ).start()

            except Exception:
                pass

            # Sleep 15 seconds between scheduler checks
            for _ in range(15):
                if not self._running:
                    break
                time.sleep(1)

    def _execute_workflow_async(
        self,
        workflow: Dict[str, Any],
        trigger_source: str,
        trigger_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a workflow graph and persist the execution record to history."""
        from locallm.core.orchestrator.graph_executor import WorkflowGraphExecutor

        wf_id = workflow.get("id", "unknown")
        wf_title = workflow.get("name") or workflow.get("title") or wf_id
        nodes = workflow.get("nodes") or []
        edges = workflow.get("edges") or []

        run_id = f"run-{uuid.uuid4().hex[:12]}"
        started_at = datetime.now()

        initial_state: Dict[str, Any] = {
            "objective": trigger_payload.get("inbound_message") or trigger_payload.get("query") or f"Automated trigger via {trigger_source.upper()}",
            "context_variables": {
                "trigger_source": trigger_source,
                "trigger_payload": trigger_payload,
                **trigger_payload,
            }
        }

        executor = WorkflowGraphExecutor(self.config, self.client)
        try:
            res = executor.run(
                nodes=nodes,
                edges=edges,
                initial_state=initial_state,
                workspace_name="default",
                execution_mode="real",
            )
            duration = (datetime.now() - started_at).total_seconds()
            status = "success" if res.get("success") else "failed"

            history_record = {
                "run_id": run_id,
                "workflow_id": wf_id,
                "workflow_title": wf_title,
                "trigger_source": trigger_source,
                "status": status,
                "started_at": started_at.isoformat(),
                "ended_at": datetime.now().isoformat(),
                "duration_seconds": round(duration, 2),
                "steps_executed": res.get("steps_executed", 0),
                "logs": res.get("logs", []),
                "artifacts": res.get("state", {}).get("artifacts", []),
                "state_summary": {
                    "objective": res.get("state", {}).get("objective"),
                    "verdict": res.get("state", {}).get("verdict"),
                    "findings_count": len(res.get("state", {}).get("findings", [])),
                    "modified_files": res.get("state", {}).get("modified_files", []),
                }
            }
            self.registry.record_execution(history_record)
            res["run_id"] = run_id
            res["duration_seconds"] = duration
            return res

        except Exception as exc:
            duration = (datetime.now() - started_at).total_seconds()
            history_record = {
                "run_id": run_id,
                "workflow_id": wf_id,
                "workflow_title": wf_title,
                "trigger_source": trigger_source,
                "status": "failed",
                "started_at": started_at.isoformat(),
                "ended_at": datetime.now().isoformat(),
                "duration_seconds": round(duration, 2),
                "steps_executed": 0,
                "logs": [{"timestamp": datetime.now().strftime("%H:%M:%S"), "agent": "TriggerEngine", "event_type": "error", "message": str(exc)}],
                "artifacts": [],
                "error": str(exc),
            }
            self.registry.record_execution(history_record)
            return {"success": False, "error": str(exc), "run_id": run_id}

    def match_and_trigger_messaging(
        self,
        platform: str,
        sender: str,
        message_text: str,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate if incoming chat matches any active workflow with a messaging-trigger node.

        Returns execution result dict if triggered, or None if no matching workflow found.
        """
        clean_platform = platform.strip().lower()
        active_workflows = self.registry.get_active_workflows()

        for wf in active_workflows:
            nodes = wf.get("nodes") or []
            msg_node = next(
                (n for n in nodes if (n.get("tag") or "").lower() == "messaging-trigger" or ("messaging" in (n.get("title") or "").lower() and "dispatcher" not in (n.get("title") or "").lower())),
                None
            )
            if not msg_node:
                continue

            props = msg_node.get("resolved_properties") or msg_node.get("properties") or {}
            inputs = props.get("inputs", {})
            options = props.get("options", {})
            cfg = msg_node.get("config", {})

            target_platform = str(options.get("platform") or cfg.get("platform") or "all").strip().lower()
            if target_platform not in ("all", "*", clean_platform):
                continue

            # Check optional keyword filter
            keyword_filter = str(inputs.get("keyword") or options.get("keyword") or cfg.get("keyword") or "").strip().lower()
            if keyword_filter and keyword_filter not in message_text.lower():
                continue

            # Match confirmed: execute workflow
            trigger_payload = {
                "inbound_message": message_text,
                "message": message_text,
                "sender": sender,
                "platform": clean_platform,
                "query": message_text,
            }
            res = self._execute_workflow_async(wf, clean_platform, trigger_payload)

            # Extract final message deliverable
            st = res.get("state", {})
            final_msg = (
                st.get("context_variables", {}).get("final_chat_message")
                or (st.get("artifacts")[-1].get("content") if st.get("artifacts") else None)
                or f"Workflow '{wf.get('name')}' completed successfully ({res.get('steps_executed', 0)} steps)."
            )

            return {
                "executed": True,
                "workflow_id": wf.get("id"),
                "workflow_title": wf.get("name") or wf.get("title"),
                "output_message": final_msg,
                "summary": f"Triggered workflow '{wf.get('name')}' from {clean_platform.upper()} chat.",
                "result": res,
            }

        return None

    def match_and_trigger_webhook(
        self,
        slug: str,
        payload: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Evaluate if an inbound HTTP webhook POST matches an active workflow webhook node."""
        clean_slug = slug.strip().strip("/")
        active_workflows = self.registry.get_active_workflows()

        for wf in active_workflows:
            nodes = wf.get("nodes") or []
            webhook_node = next(
                (n for n in nodes if (n.get("tag") or "").lower() == "webhook" or "webhook" in (n.get("title") or "").lower()),
                None
            )
            if not webhook_node:
                continue

            props = webhook_node.get("resolved_properties") or webhook_node.get("properties") or {}
            inputs = props.get("inputs", {})
            cfg = webhook_node.get("config", {})

            configured_endpoint = str(
                inputs.get("endpoint") or inputs.get("path") or cfg.get("endpoint") or cfg.get("path") or "webhook"
            ).strip().strip("/")
            configured_slug = configured_endpoint.split("/")[-1]

            if clean_slug == configured_slug or clean_slug == configured_endpoint or configured_endpoint in ("*", "all"):
                trigger_payload = {
                    "webhook_slug": clean_slug,
                    "payload": payload,
                    "query": f"Inbound Webhook [{clean_slug}] Event",
                    "inbound_message": json.dumps(payload, ensure_ascii=False) if payload else f"Webhook {clean_slug}",
                }
                res = self._execute_workflow_async(wf, "webhook", trigger_payload)
                return {
                    "executed": True,
                    "workflow_id": wf.get("id"),
                    "workflow_title": wf.get("name") or wf.get("title"),
                    "result": res,
                }

        return None


# Global trigger engine access
_TRIGGER_ENGINE: Optional[WorkflowTriggerEngine] = None

def get_trigger_engine(config: Optional[LocaLLMConfig] = None, client: Optional[Any] = None) -> WorkflowTriggerEngine:
    """Retrieve the global WorkflowTriggerEngine singleton."""
    global _TRIGGER_ENGINE
    if _TRIGGER_ENGINE is None:
        _TRIGGER_ENGINE = WorkflowTriggerEngine(config=config, client=client)
    return _TRIGGER_ENGINE
