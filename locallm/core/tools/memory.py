"""Memory management tools for persistent user preferences and facts across workspaces."""

import json
import re
from typing import Any, Dict, Optional

from locallm.core.global_memory import GlobalMemoryManager
from locallm.core.tools.base import tool

# Sensitive patterns that must never be stored in global memory
SENSITIVE_PATTERNS = [
    r"(?i)\b(sk-[a-zA-Z0-9_\-]{16,})\b",
    r"(?i)\b(ghp_[a-zA-Z0-9]{30,}|gho_[a-zA-Z0-9]{30,})\b",
    r"(?i)\b(bearer\s+[a-zA-Z0-9_\-\.]{20,})\b",
    r"(?i)\b(password|passwd|secret_key|api_key|access_token)\s*[:=]\s*['\"][^'\"]{6,}['\"]",
]


def update_user_memory_fn(
    action: str,
    category: str,
    key: Optional[str] = None,
    value: Optional[Any] = None,
    **kwargs: Any,
) -> str:
    """Update or delete entries in persistent global user memory.

    Action must be 'set' or 'delete'.
    Category must be 'user_profile', 'communication_rules', or 'facts'.
    """
    clean_action = str(action or "").strip().lower()
    clean_category = str(category or "").strip().lower()

    if clean_action not in ("set", "delete"):
        return f"Error: Invalid action '{action}'. Allowed actions are 'set' or 'delete'."

    valid_categories = {
        "user_profile": "user_profile",
        "profile": "user_profile",
        "communication_rules": "communication_rules",
        "rules": "communication_rules",
        "rule": "communication_rules",
        "facts": "facts",
        "fact": "facts",
    }
    if clean_category not in valid_categories:
        return (
            f"Error: Invalid category '{category}'. Allowed categories are "
            "'user_profile', 'communication_rules', or 'facts'."
        )
    target_category = valid_categories[clean_category]

    mgr = GlobalMemoryManager()

    if clean_action == "set":
        # 1. Sanitize raw value to prevent storing secrets or sensitive credentials
        val_str = str(value) if value is not None else (str(key) if key else "")
        for pat in SENSITIVE_PATTERNS:
            if re.search(pat, val_str) or (key and re.search(pat, str(key))):
                return "Error: Security policy prevents storing sensitive secrets, passwords, or API keys in persistent global memory."

        # 2. Sanitize to prevent raw Chain-of-Thought leakage
        if value is not None and isinstance(value, str):
            clean_v = re.sub(r"<(?:think|thought)>[\s\S]*?</(?:think|thought)>", "", value)
            clean_v = re.sub(r"<(?:think|thought)>[\s\S]*$", "", clean_v).strip()
            value = clean_v

        if target_category == "communication_rules":
            rule_content = value if value is not None else key
            if not rule_content or not str(rule_content).strip():
                return "Error: A rule statement must be provided in 'value' (or 'key') for category 'communication_rules'."
            success = mgr.set_fact("communication_rules", "", str(rule_content).strip())
            if success:
                return f"Successfully added communication rule to global memory: '{rule_content}'"
            return "Failed to save communication rule to global memory."

        else:
            if not key or not str(key).strip():
                return f"Error: A 'key' identifier is required to set an entry in '{target_category}'."
            clean_key = str(key).strip()
            success = mgr.set_fact(target_category, clean_key, value)
            if success:
                return f"Successfully saved to global memory [{target_category}] -> {clean_key}: {value}"
            return f"Failed to save {clean_key} to global memory."

    elif clean_action == "delete":
        target_key = str(key).strip() if key else (str(value).strip() if value else "")
        if not target_key:
            return f"Error: A 'key' (or rule text) is required to delete an entry from '{target_category}'."

        success = mgr.delete_fact(target_category, target_key)
        if success:
            return f"Successfully removed '{target_key}' from global memory [{target_category}]."
        return f"Entry '{target_key}' was not found in global memory [{target_category}]."

    return "No memory operation performed."


tool(
    name="update_user_memory",
    description=(
        "Update the persistent cross-workspace user memory for durable facts, user profile, or communication rules. "
        "Use ONLY when the user explicitly requests to remember/forget something or for clear, stable facts/preferences "
        "(e.g., user name, preferred language, concise style rule). "
        "DO NOT use for temporary requests, casual conversation, secrets/passwords, or internal reasoning."
    ),
    parameters={
        "type": "object",
        "required": ["action", "category"],
        "properties": {
            "action": {
                "type": "string",
                "enum": ["set", "delete"],
                "description": "Action to perform: 'set' to store or update, 'delete' to remove.",
            },
            "category": {
                "type": "string",
                "enum": ["user_profile", "communication_rules", "facts"],
                "description": "Target memory category: 'user_profile' (identity/role), 'communication_rules' (interaction style/rules), or 'facts' (durable user facts).",
            },
            "key": {
                "type": "string",
                "description": "Key identifier for user_profile or facts (e.g. 'preferred_language', 'name'). For communication_rules, this can be the rule text if value is not provided.",
            },
            "value": {
                "description": "The information or rule to remember (string, number, boolean, or structured object).",
            },
        },
    },
    is_mutating=True,
    categories={"assistant", "telegram", "whatsapp"},
)(update_user_memory_fn)
