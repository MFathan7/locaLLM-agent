"""Property schema and dynamic variable interpolation engine for Visual Workflow Activities.

Provides complete activity schemas, default properties structure (Common, Inputs, Options, Output),
and runtime interpolation for {{variable}} and {{node_id.output}} expressions against the blackboard state.
"""

from copy import deepcopy
import re
from typing import Any, Dict, List, Optional, Union


# -------------------------------------------------------------------------
# Dynamic Property Schema Definitions
# -------------------------------------------------------------------------

COMMON_PROPERTY_FIELDS: List[Dict[str, Any]] = [
    {
        "name": "displayName",
        "label": "Display Name",
        "type": "text",
        "description": "Human-readable activity name displayed on canvas.",
        "defaultValue": "",
    },
    {
        "name": "description",
        "label": "Description",
        "type": "multiline",
        "description": "Operational notes and purpose of this activity instance.",
        "defaultValue": "",
    },
    {
        "name": "continueOnError",
        "label": "Continue on Error",
        "type": "boolean",
        "description": "If true, workflow continues execution downstream even if this activity errors.",
        "defaultValue": False,
    },
    {
        "name": "timeoutSeconds",
        "label": "Timeout (Seconds)",
        "type": "number",
        "description": "Maximum allowable execution duration before interrupting activity.",
        "defaultValue": 60,
    },
]

ACTIVITY_PROPERTY_SCHEMAS: Dict[str, Dict[str, Any]] = {
    # 1. Triggers
    "intake": {
        "tag": "intake",
        "title": "User Objective Input",
        "category": "triggers",
        "inputs": [
            {
                "name": "query",
                "label": "Task Objective",
                "type": "multiline",
                "description": "Primary objective or task directive to execute.",
                "defaultValue": "Analyze project codebase",
                "supportVariables": True,
            },
            {
                "name": "workspace",
                "label": "Workspace Boundary",
                "type": "text",
                "description": "Target project workspace for file and context operations.",
                "defaultValue": "default",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "sourceType",
                "label": "Input Source",
                "type": "select",
                "defaultValue": "manual",
                "options": ["manual", "api"],
            }
        ],
        "defaultOutputVariable": "out_user_objective",
        "outputDescription": "Stores captured user objective string.",
    },

    "messaging-trigger": {
        "tag": "messaging-trigger",
        "title": "Messaging Trigger",
        "category": "triggers",
        "inputs": [
            {
                "name": "messageTemplate",
                "label": "Inbound Message Content",
                "type": "multiline",
                "description": "Inbound message content from Telegram or WhatsApp bridge.",
                "defaultValue": "Tolong carikan surat Al-Kahfi ayat 1 sampai 10",
                "supportVariables": True,
            },
            {
                "name": "allowedUsers",
                "label": "Allowed Users",
                "type": "text",
                "defaultValue": "@ops_admin, @lead_dev",
                "supportVariables": False,
            },
        ],
        "options": [
            {
                "name": "platform",
                "label": "Messaging Platform",
                "type": "select",
                "defaultValue": "telegram",
                "options": ["telegram", "whatsapp", "discord"],
            }
        ],
        "defaultOutputVariable": "out_trigger_payload",
        "outputDescription": "Stores parsed incoming message text and sender details.",
    },

    "schedule-trigger": {
        "tag": "schedule-trigger",
        "title": "Schedule Trigger",
        "category": "triggers",
        "inputs": [
            {
                "name": "cron",
                "label": "Cron Expression",
                "type": "text",
                "defaultValue": "0 2 * * *",
                "supportVariables": False,
            },
            {
                "name": "query",
                "label": "Routine Mission Description",
                "type": "text",
                "defaultValue": "Automated System Audit & Maintenance Routine",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "timezone",
                "label": "Timezone",
                "type": "select",
                "defaultValue": "Asia/Jakarta",
                "options": ["Asia/Jakarta", "UTC", "America/New_York", "Europe/London"],
            }
        ],
        "defaultOutputVariable": "out_schedule_event",
        "outputDescription": "Stores cron timestamp and scheduled run metadata.",
    },

    "webhook": {
        "tag": "webhook",
        "title": "Webhook Trigger",
        "category": "triggers",
        "inputs": [
            {
                "name": "endpoint",
                "label": "REST Endpoint Path",
                "type": "text",
                "defaultValue": "/api/v1/webhook",
                "supportVariables": False,
            },
            {
                "name": "workspace",
                "label": "Workspace",
                "type": "text",
                "defaultValue": "default",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "httpMethod",
                "label": "HTTP Method",
                "type": "select",
                "defaultValue": "POST",
                "options": ["POST", "GET"],
            }
        ],
        "defaultOutputVariable": "out_webhook_payload",
        "outputDescription": "Stores parsed JSON request body and headers.",
    },

    # 2. Orchestration
    "supervisor": {
        "tag": "supervisor",
        "title": "Supervisor / Coordinator",
        "category": "orchestration",
        "inputs": [
            {
                "name": "directive",
                "label": "Supervisor Directive",
                "type": "multiline",
                "defaultValue": "Coordinate tasks and maintain blackboard state",
                "supportVariables": True,
            },
            {
                "name": "workspace",
                "label": "Workspace",
                "type": "text",
                "defaultValue": "default",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "model",
                "label": "AI Reasoning Model",
                "type": "select",
                "defaultValue": "auto",
                "options": ["auto", "qwen3.5:9b", "gemma4:12b", "gemma4:26b", "nemotron3-super"],
            },
            {
                "name": "temperature",
                "label": "Temperature",
                "type": "slider",
                "defaultValue": 0.2,
                "min": 0,
                "max": 1,
            },
            {
                "name": "maxRetries",
                "label": "Max Subtask Retries",
                "type": "number",
                "defaultValue": 2,
            },
        ],
        "defaultOutputVariable": "out_supervisor_directive",
        "outputDescription": "Stores supervisor synthesis and subtask status.",
    },

    "task-decomposer": {
        "tag": "task-decomposer",
        "title": "Task Decomposer (Planner)",
        "category": "orchestration",
        "inputs": [
            {
                "name": "objective",
                "label": "Objective to Decompose",
                "type": "multiline",
                "defaultValue": "{{out_user_objective}}",
                "supportVariables": True,
            }
        ],
        "options": [
            {
                "name": "max_subtasks",
                "label": "Max Subtasks",
                "type": "number",
                "defaultValue": 4,
            },
            {
                "name": "strategy",
                "label": "Decomposition Strategy",
                "type": "select",
                "defaultValue": "hierarchical",
                "options": ["hierarchical", "sequential", "dynamic"],
            },
        ],
        "defaultOutputVariable": "out_task_queue",
        "outputDescription": "List of decomposed subtask descriptions.",
    },

    "model-router": {
        "tag": "model-router",
        "title": "Dynamic Model Router",
        "category": "orchestration",
        "inputs": [],
        "options": [
            {
                "name": "vram_threshold_mb",
                "label": "VRAM Threshold (MB)",
                "type": "number",
                "defaultValue": 8192,
            },
            {
                "name": "fast_model",
                "label": "Fast Tier Model",
                "type": "text",
                "defaultValue": "gemma4:12b",
            },
            {
                "name": "deep_model",
                "label": "Deep Tier Model",
                "type": "text",
                "defaultValue": "gemma4:26b",
            },
        ],
        "defaultOutputVariable": "out_selected_model",
        "outputDescription": "Selected model identifier string based on GPU telemetry.",
    },

    "intent-switch": {
        "tag": "intent-switch",
        "title": "Semantic Intent Switch",
        "category": "orchestration",
        "inputs": [
            {
                "name": "query",
                "label": "Input Prompt for Classification",
                "type": "multiline",
                "defaultValue": "{{out_user_objective}}",
                "supportVariables": True,
            }
        ],
        "options": [
            {
                "name": "branches",
                "label": "Supported Intent Branches",
                "type": "tags",
                "defaultValue": ["CODING", "REASONING", "TOOLS", "FAST_CHAT"],
            }
        ],
        "defaultOutputVariable": "out_detected_intent",
        "outputDescription": "Detected intent label string matching outgoing branches.",
    },

    "parallel-aggregator": {
        "tag": "parallel-aggregator",
        "title": "Parallel Aggregator",
        "category": "orchestration",
        "inputs": [
            {
                "name": "mergeFields",
                "label": "Fields to Merge",
                "type": "text",
                "defaultValue": "findings, artifacts, context_variables",
            }
        ],
        "options": [
            {
                "name": "join_strategy",
                "label": "Join Strategy",
                "type": "select",
                "defaultValue": "all_completed",
                "options": ["all_completed", "first_success"],
            },
            {
                "name": "timeout",
                "label": "Timeout (Seconds)",
                "type": "number",
                "defaultValue": 60,
            },
        ],
        "defaultOutputVariable": "out_aggregated_data",
        "outputDescription": "Merged dictionary of parallel specialist outputs.",
    },

    # 3. Specialists
    "researcher": {
        "tag": "researcher",
        "title": "Researcher Agent",
        "category": "specialists",
        "inputs": [
            {
                "name": "searchQuery",
                "label": "Research Query / Target",
                "type": "multiline",
                "defaultValue": "{{out_user_objective}}",
                "supportVariables": True,
            },
            {
                "name": "api_base",
                "label": "External API Base URL",
                "type": "text",
                "defaultValue": "https://equran.id/api/v2",
                "supportVariables": True,
            },
            {
                "name": "reciter",
                "label": "Audio Reciter Stream",
                "type": "text",
                "defaultValue": "Misyari-Rasyid-Al-Afasi",
            },
        ],
        "options": [
            {
                "name": "model",
                "label": "Model",
                "type": "select",
                "defaultValue": "auto",
                "options": ["auto", "qwen3.5:9b", "gemma4:12b", "nemotron3-super"],
            },
            {
                "name": "temperature",
                "label": "Temperature",
                "type": "slider",
                "defaultValue": 0.3,
            },
            {
                "name": "retrievalTopK",
                "label": "Retrieval Top K",
                "type": "number",
                "defaultValue": 4,
            },
            {
                "name": "tools",
                "label": "Active Tools",
                "type": "tags",
                "defaultValue": ["search_web", "fetch_web", "read_file"],
            },
        ],
        "defaultOutputVariable": "out_research_data",
        "outputDescription": "Research findings, citations, and API responses.",
    },

    "coder": {
        "tag": "coder",
        "title": "Coder Agent",
        "category": "specialists",
        "inputs": [
            {
                "name": "taskDescription",
                "label": "Coding Task / Instruction",
                "type": "multiline",
                "defaultValue": "{{out_user_objective}}",
                "supportVariables": True,
            },
            {
                "name": "output_file",
                "label": "Patch Output File Path",
                "type": "text",
                "defaultValue": "docs/patch_revision.diff",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "model",
                "label": "Coding Model",
                "type": "select",
                "defaultValue": "auto",
                "options": ["auto", "qwen3.5:9b", "gemma4:26b", "nemotron3-super"],
            },
            {
                "name": "temperature",
                "label": "Temperature",
                "type": "slider",
                "defaultValue": 0.1,
            },
            {
                "name": "tools",
                "label": "Active Tools",
                "type": "tags",
                "defaultValue": ["patch_file", "write_file", "check_syntax"],
            },
        ],
        "defaultOutputVariable": "out_patch_diff",
        "outputDescription": "Generated unified diff patch and modified file paths.",
    },

    "data-analyst": {
        "tag": "data-analyst",
        "title": "Data/DB Analyst",
        "category": "specialists",
        "inputs": [
            {
                "name": "sqlQuery",
                "label": "SQL Diagnostic Query",
                "type": "multiline",
                "defaultValue": "SELECT service, status, last_heartbeat FROM system_services ORDER BY last_heartbeat DESC LIMIT 10;",
                "supportVariables": True,
            },
            {
                "name": "db_path",
                "label": "Database File Path",
                "type": "text",
                "defaultValue": "locallm_ops.db",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "maxRows",
                "label": "Max Return Rows",
                "type": "number",
                "defaultValue": 50,
            },
            {
                "name": "readOnly",
                "label": "Enforce Read-Only",
                "type": "boolean",
                "defaultValue": True,
            },
        ],
        "defaultOutputVariable": "out_query_results",
        "outputDescription": "SQL query results table and column headers.",
    },

    "critic": {
        "tag": "critic",
        "title": "Critic / QA Agent",
        "category": "specialists",
        "inputs": [
            {
                "name": "validationCriteria",
                "label": "Verification Criteria",
                "type": "multiline",
                "defaultValue": "Verify AST syntax, unit tests, and regression safety.",
                "supportVariables": True,
            },
            {
                "name": "targetArtifact",
                "label": "Target Artifact Reference",
                "type": "text",
                "defaultValue": "{{out_patch_diff}}",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "pass_threshold",
                "label": "Passing Score Threshold (0-100)",
                "type": "slider",
                "defaultValue": 85,
            },
            {
                "name": "model",
                "label": "Evaluation Model",
                "type": "select",
                "defaultValue": "auto",
                "options": ["auto", "qwen3.5:9b", "gemma4:26b"],
            },
        ],
        "defaultOutputVariable": "out_qa_verdict",
        "outputDescription": "Evaluation dictionary with passed flag, score, and feedback.",
    },

    "writer": {
        "tag": "writer",
        "title": "Writer Agent",
        "category": "specialists",
        "inputs": [
            {
                "name": "systemPrompt",
                "label": "System Prompt / Persona",
                "type": "multiline",
                "defaultValue": "You are an elite technical documentation specialist. Author comprehensive, structured reports.",
                "supportVariables": True,
            },
            {
                "name": "messageTemplate",
                "label": "Report Body Template",
                "type": "multiline",
                "defaultValue": "# Deliverable for {{out_user_objective}}\n\n## Summary\n{{out_research_data}}",
                "supportVariables": True,
            },
            {
                "name": "output_file",
                "label": "Document Destination Path",
                "type": "text",
                "defaultValue": "docs/market_intelligence_report.md",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "format",
                "label": "Export Format",
                "type": "select",
                "defaultValue": "markdown",
                "options": ["markdown", "json", "html"],
            },
            {
                "name": "model",
                "label": "Drafting Model",
                "type": "select",
                "defaultValue": "auto",
                "options": ["auto", "qwen3.5:9b", "gemma4:12b"],
            },
            {
                "name": "temperature",
                "label": "Temperature",
                "type": "slider",
                "defaultValue": 0.35,
            },
        ],
        "defaultOutputVariable": "out_written_doc",
        "outputDescription": "Drafted report text content in markdown or HTML.",
    },

    "custom-specialist": {
        "tag": "custom-specialist",
        "title": "Custom Specialist",
        "category": "specialists",
        "inputs": [
            {
                "name": "role",
                "label": "Role Designation",
                "type": "text",
                "defaultValue": "Domain Specialist",
                "supportVariables": True,
            },
            {
                "name": "directive",
                "label": "Operating Directive",
                "type": "multiline",
                "defaultValue": "Execute specialized domain instructions",
                "supportVariables": True,
            },
            {
                "name": "inputContext",
                "label": "Input Context",
                "type": "multiline",
                "defaultValue": "{{out_user_objective}}",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "model",
                "label": "Model",
                "type": "select",
                "defaultValue": "auto",
                "options": ["auto", "qwen3.5:9b", "gemma4:12b"],
            },
            {
                "name": "temperature",
                "label": "Temperature",
                "type": "slider",
                "defaultValue": 0.3,
            },
        ],
        "defaultOutputVariable": "out_specialist_result",
        "outputDescription": "Execution result produced by custom specialist.",
    },

    # 4. State & Knowledge
    "blackboard": {
        "tag": "blackboard",
        "title": "Blackboard Hub (Shared State)",
        "category": "state_knowledge",
        "inputs": [
            {
                "name": "workspace",
                "label": "Workspace Key",
                "type": "text",
                "defaultValue": "default",
                "supportVariables": True,
            }
        ],
        "options": [
            {
                "name": "syncIntervalSeconds",
                "label": "Sync Interval (Seconds)",
                "type": "number",
                "defaultValue": 5,
            }
        ],
        "defaultOutputVariable": "out_blackboard_state",
        "outputDescription": "Central blackboard state snapshot.",
    },

    "rag-retriever": {
        "tag": "rag-retriever",
        "title": "RAG Retriever",
        "category": "state_knowledge",
        "inputs": [
            {
                "name": "searchQuery",
                "label": "Knowledge Query",
                "type": "multiline",
                "defaultValue": "{{out_user_objective}}",
                "supportVariables": True,
            },
            {
                "name": "workspace",
                "label": "Workspace",
                "type": "text",
                "defaultValue": "default",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "top_k",
                "label": "Top K Passages",
                "type": "slider",
                "defaultValue": 4,
            }
        ],
        "defaultOutputVariable": "out_rag_passages",
        "outputDescription": "Ranked passages retrieved from knowledge store.",
    },

    "memory-rw": {
        "tag": "memory-rw",
        "title": "Memory R/W",
        "category": "state_knowledge",
        "inputs": [
            {
                "name": "key",
                "label": "Memory Key",
                "type": "text",
                "defaultValue": "system_preferences",
                "supportVariables": True,
            },
            {
                "name": "value",
                "label": "Memory Value",
                "type": "multiline",
                "defaultValue": "",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "mode",
                "label": "Access Mode",
                "type": "select",
                "defaultValue": "read_write",
                "options": ["read_write", "read", "write"],
            },
            {
                "name": "scope",
                "label": "Storage Scope",
                "type": "select",
                "defaultValue": "workspace",
                "options": ["workspace", "global"],
            },
        ],
        "defaultOutputVariable": "out_memory_value",
        "outputDescription": "Persisted value read from memory storage.",
    },

    "context-compressor": {
        "tag": "context-compressor",
        "title": "Context Compressor",
        "category": "state_knowledge",
        "inputs": [
            {
                "name": "contextInput",
                "label": "Context to Compress",
                "type": "multiline",
                "defaultValue": "{{out_research_data}}",
                "supportVariables": True,
            }
        ],
        "options": [
            {
                "name": "max_tokens",
                "label": "Max Tokens",
                "type": "number",
                "defaultValue": 3000,
            }
        ],
        "defaultOutputVariable": "out_compressed_context",
        "outputDescription": "Token-pruned concise context summary.",
    },

    # 5. Tools & Plugins
    "mcp-tool": {
        "tag": "mcp-tool",
        "title": "MCP Tool",
        "category": "tools_plugins",
        "inputs": [
            {
                "name": "server",
                "label": "MCP Server ID",
                "type": "text",
                "defaultValue": "local",
                "supportVariables": False,
            },
            {
                "name": "tool_name",
                "label": "Tool Name",
                "type": "text",
                "defaultValue": "inspect",
                "supportVariables": True,
            },
            {
                "name": "arguments",
                "label": "Arguments (JSON)",
                "type": "json",
                "defaultValue": "{}",
                "supportVariables": True,
            },
        ],
        "options": [],
        "defaultOutputVariable": "out_mcp_result",
        "outputDescription": "Tool execution result from MCP server.",
    },

    "filesystem": {
        "tag": "filesystem",
        "title": "Filesystem",
        "category": "tools_plugins",
        "inputs": [
            {
                "name": "path",
                "label": "Path",
                "type": "text",
                "defaultValue": ".",
                "supportVariables": True,
            },
            {
                "name": "fileContent",
                "label": "File Content",
                "type": "multiline",
                "defaultValue": "",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "operation",
                "label": "Operation",
                "type": "select",
                "defaultValue": "read",
                "options": ["read", "write", "list"],
            },
            {
                "name": "workspace",
                "label": "Workspace",
                "type": "text",
                "defaultValue": "default",
                "supportVariables": True,
            },
        ],
        "defaultOutputVariable": "out_fs_result",
        "outputDescription": "File content string or directory listings.",
    },

    "subprocess": {
        "tag": "subprocess",
        "title": "Shell Runner",
        "category": "tools_plugins",
        "inputs": [
            {
                "name": "command",
                "label": "Shell Command",
                "type": "multiline",
                "defaultValue": "pytest -q",
                "supportVariables": True,
            },
            {
                "name": "workingDir",
                "label": "Working Directory",
                "type": "text",
                "defaultValue": ".",
                "supportVariables": True,
            },
        ],
        "options": [],
        "defaultOutputVariable": "out_shell_stdout",
        "outputDescription": "Subprocess exit code, stdout, and stderr logs.",
    },

    "online-web": {
        "tag": "online-web",
        "title": "Web Search",
        "category": "tools_plugins",
        "inputs": [
            {
                "name": "query",
                "label": "Search Query",
                "type": "multiline",
                "defaultValue": "{{out_user_objective}}",
                "supportVariables": True,
            }
        ],
        "options": [
            {
                "name": "provider",
                "label": "Provider",
                "type": "select",
                "defaultValue": "auto",
                "options": ["auto", "bing", "duckduckgo"],
            },
            {
                "name": "max_results",
                "label": "Max Results",
                "type": "number",
                "defaultValue": 5,
            },
        ],
        "defaultOutputVariable": "out_web_results",
        "outputDescription": "Web search result citations and snippets.",
    },

    "plugin-executor": {
        "tag": "plugin-executor",
        "title": "Plugin Executor",
        "category": "tools_plugins",
        "inputs": [
            {
                "name": "plugin_id",
                "label": "Plugin ID",
                "type": "text",
                "defaultValue": "default",
                "supportVariables": True,
            },
            {
                "name": "actionPayload",
                "label": "Action Payload (JSON)",
                "type": "json",
                "defaultValue": "{}",
                "supportVariables": True,
            },
        ],
        "options": [],
        "defaultOutputVariable": "out_plugin_result",
        "outputDescription": "Output dictionary returned from plugin function.",
    },

    # 6. Flow Control
    "quality-gate": {
        "tag": "quality-gate",
        "title": "Quality Gate (If/Else)",
        "category": "flow_control",
        "inputs": [
            {
                "name": "condition",
                "label": "Condition Expression",
                "type": "text",
                "defaultValue": "verdict.passed == true",
                "supportVariables": True,
            }
        ],
        "options": [
            {
                "name": "max_retries",
                "label": "Max Retries",
                "type": "number",
                "defaultValue": 2,
            },
            {
                "name": "min_score",
                "label": "Minimum Pass Score",
                "type": "slider",
                "defaultValue": 80,
            },
        ],
        "defaultOutputVariable": "out_gate_decision",
        "outputDescription": "Decision routing token ('true' or 'loop').",
    },

    "task-iterator": {
        "tag": "task-iterator",
        "title": "Sub-Task Iterator (ForEach)",
        "category": "flow_control",
        "inputs": [
            {
                "name": "queueVariable",
                "label": "Target Queue Variable",
                "type": "text",
                "defaultValue": "task_queue",
                "supportVariables": True,
            }
        ],
        "options": [
            {
                "name": "batch_size",
                "label": "Batch Size",
                "type": "number",
                "defaultValue": 1,
            }
        ],
        "defaultOutputVariable": "out_current_item",
        "outputDescription": "Item extracted for active subtask iteration.",
    },

    "policy-gate": {
        "tag": "policy-gate",
        "title": "Human Approval",
        "category": "flow_control",
        "inputs": [
            {
                "name": "promptMessage",
                "label": "Approval Prompt",
                "type": "multiline",
                "defaultValue": "Action Required: Pending maintenance update ready. Awaiting admin approval via web console.",
                "supportVariables": True,
            }
        ],
        "options": [
            {
                "name": "policy",
                "label": "Policy Mode",
                "type": "select",
                "defaultValue": "ask",
                "options": ["ask", "auto"],
            },
            {
                "name": "timeout_seconds",
                "label": "Timeout (Seconds)",
                "type": "number",
                "defaultValue": 120,
            },
        ],
        "defaultOutputVariable": "out_approval_status",
        "outputDescription": "Authorization verdict ('approved' or 'rejected').",
    },

    "try-catch": {
        "tag": "try-catch",
        "title": "Try-Catch",
        "category": "flow_control",
        "inputs": [],
        "options": [
            {
                "name": "max_error_retries",
                "label": "Max Retries",
                "type": "number",
                "defaultValue": 1,
            }
        ],
        "defaultOutputVariable": "out_error_info",
        "outputDescription": "Captured error message and failure context.",
    },

    # 7. Outputs
    "chat-output": {
        "tag": "chat-output",
        "title": "Chat & Artifact Output",
        "category": "outputs",
        "inputs": [
            {
                "name": "message",
                "label": "Final Message Template",
                "type": "multiline",
                "defaultValue": "Objective accomplished: {{out_user_objective}}.",
                "supportVariables": True,
            },
            {
                "name": "output_file",
                "label": "Audit Report File Path",
                "type": "text",
                "defaultValue": "docs/audit_report.md",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "notify_user",
                "label": "Notify User",
                "type": "boolean",
                "defaultValue": True,
            }
        ],
        "defaultOutputVariable": "out_chat_deliverable",
        "outputDescription": "Final conversation answer and created file details.",
    },

    "doc-exporter": {
        "tag": "doc-exporter",
        "title": "Document Exporter",
        "category": "outputs",
        "inputs": [
            {
                "name": "output_path",
                "label": "Output File Path",
                "type": "text",
                "defaultValue": "docs/workflow_report.md",
                "supportVariables": True,
            },
            {
                "name": "contentTemplate",
                "label": "Content Template",
                "type": "multiline",
                "defaultValue": "",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "format",
                "label": "Export Format",
                "type": "select",
                "defaultValue": "markdown",
                "options": ["markdown", "json", "html"],
            },
            {
                "name": "notify_user",
                "label": "Notify User via Telegram",
                "type": "boolean",
                "defaultValue": True,
            },
        ],
        "defaultOutputVariable": "out_exported_file",
        "outputDescription": "Exported file path, size, and metadata record.",
    },

    "messaging-dispatcher": {
        "tag": "messaging-dispatcher",
        "title": "Messaging Dispatcher",
        "category": "outputs",
        "inputs": [
            {
                "name": "recipient",
                "label": "Recipient Chat ID / Handle",
                "type": "text",
                "defaultValue": "@ops_admin",
                "supportVariables": True,
            },
            {
                "name": "messageTemplate",
                "label": "Message Template",
                "type": "multiline",
                "defaultValue": "",
                "supportVariables": True,
            },
        ],
        "options": [
            {
                "name": "channel",
                "label": "Channel",
                "type": "select",
                "defaultValue": "telegram",
                "options": ["telegram", "whatsapp", "discord"],
            }
        ],
        "defaultOutputVariable": "out_dispatch_receipt",
        "outputDescription": "Receipt record confirming message dispatch status.",
    },
}


def get_property_schema_for_activity(tag: str) -> Dict[str, Any]:
    """Retrieve PropertySchema for an activity tag with safe fallback."""
    clean_tag = (tag or "").lower().strip()
    if clean_tag in ACTIVITY_PROPERTY_SCHEMAS:
        return ACTIVITY_PROPERTY_SCHEMAS[clean_tag]

    return {
        "tag": clean_tag or "custom",
        "title": "Custom Activity",
        "category": "custom",
        "inputs": [
            {
                "name": "query",
                "label": "Instruction / Query",
                "type": "multiline",
                "defaultValue": "",
                "supportVariables": True,
            }
        ],
        "options": [
            {
                "name": "model",
                "label": "Model",
                "type": "select",
                "defaultValue": "auto",
                "options": ["auto", "qwen3.5:9b", "gemma4:12b"],
            }
        ],
        "defaultOutputVariable": f"out_{re.sub(r'[^a-z0-9_]', '_', clean_tag) or 'custom'}_result",
        "outputDescription": "Result produced by this activity execution.",
    }


def get_default_properties_for_activity(
    tag: str,
    title: str = "",
    subtitle: str = "",
    legacy_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build dynamic properties dictionary for an activity, migrating legacy config if present."""
    schema = get_property_schema_for_activity(tag)
    cfg = legacy_config or {}

    inputs: Dict[str, Any] = {}
    for f in schema.get("inputs", []):
        name = f["name"]
        inputs[name] = cfg.get(name, f.get("defaultValue"))

    options: Dict[str, Any] = {}
    for f in schema.get("options", []):
        name = f["name"]
        options[name] = cfg.get(name, f.get("defaultValue"))

    # Preserve any unmapped legacy keys in options for backward compatibility
    for k, v in cfg.items():
        if k not in inputs and k not in options:
            options[k] = v

    if "parameterMode" not in options:
        cat = schema.get("category", "")
        options["parameterMode"] = cfg.get("parameterMode") or ("custom" if cat == "triggers" else "auto")

    return {
        "common": {
            "displayName": title or schema.get("title", ""),
            "description": subtitle or "",
            "continueOnError": bool(cfg.get("continueOnError", False)),
            "timeoutSeconds": int(cfg.get("timeoutSeconds", cfg.get("timeout", 60))),
        },
        "inputs": inputs,
        "options": options,
        "output": {
            "outputVariable": cfg.get("outputVariable") or schema.get("defaultOutputVariable", "out_result"),
        },
    }


get_default_properties_for_tag = get_default_properties_for_activity


def ensure_node_dynamic_properties(node: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures a node dictionary has complete dynamic properties structure."""
    if not isinstance(node, dict):
        return node

    props = node.get("properties")
    if (
        isinstance(props, dict)
        and "common" in props
        and "inputs" in props
        and "options" in props
        and "output" in props
    ):
        return node

    tag = node.get("tag", "")
    default_props = get_default_properties_for_activity(
        tag,
        title=node.get("title", ""),
        subtitle=node.get("subtitle", ""),
        legacy_config=node.get("config", {}),
    )

    if isinstance(props, dict):
        # Merge existing partial properties on top of defaults
        default_props["common"].update(props.get("common", {}))
        default_props["inputs"].update(props.get("inputs", {}))
        default_props["options"].update(props.get("options", {}))
        default_props["output"].update(props.get("output", {}))

    node_copy = deepcopy(node)
    node_copy["properties"] = default_props
    return node_copy


# -------------------------------------------------------------------------
# Dynamic Variable Interpolation Engine ({{variable}} and {{node_id.output}})
# -------------------------------------------------------------------------

_VAR_TOKEN_PATTERN = re.compile(r"\{\{([^{}]+)\}\}")


def resolve_variable_value(var_path: str, context: Dict[str, Any]) -> Any:
    """Traverses dotted or subscripted path in context dictionary.
    
    Supports:
      - out_trigger_payload
      - node_id.output
      - quran_data.namaLatin
      - verdict.score
    """
    clean_path = var_path.strip()
    if clean_path in context:
        return context[clean_path]

    parts = clean_path.split(".")
    curr: Any = context
    for p in parts:
        if isinstance(curr, dict) and p in curr:
            curr = curr[p]
        elif hasattr(curr, p):
            curr = getattr(curr, p)
        else:
            return None
    return curr


def interpolate_text_template(template_str: str, context: Dict[str, Any]) -> str:
    """Interpolates all {{variable}} tokens inside a text template string using context dictionary."""
    if not isinstance(template_str, str) or "{{" not in template_str:
        return template_str

    def _replace_token(match: re.Match) -> str:
        var_name = match.group(1).strip()
        val = resolve_variable_value(var_name, context)
        if val is None:
            # Leave token or empty string if not found
            return match.group(0)
        if isinstance(val, (dict, list)):
            import json
            try:
                return json.dumps(val, ensure_ascii=False)
            except Exception:
                return str(val)
        return str(val)

    return _VAR_TOKEN_PATTERN.sub(_replace_token, template_str)


def interpolate_properties(props: Any, context: Dict[str, Any]) -> Any:
    """Recursively interpolates {{...}} tokens across dictionaries, lists, and strings."""
    if isinstance(props, str):
        # If the whole string is exactly "{{var_name}}", return the raw object if resolved
        match = re.fullmatch(r"\{\{([^{}]+)\}\}", props.strip())
        if match:
            resolved = resolve_variable_value(match.group(1).strip(), context)
            if resolved is not None:
                return resolved
        return interpolate_text_template(props, context)
    elif isinstance(props, dict):
        return {k: interpolate_properties(v, context) for k, v in props.items()}
    elif isinstance(props, list):
        return [interpolate_properties(item, context) for item in props]
    return props
