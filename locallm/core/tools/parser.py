"""Fallback response parsing for models emitting raw or markdown JSON tool calls."""

import json
from typing import Any, Dict, List, Optional, Set
from locallm.core.tools.base import registry


def extract_fallback_tool_calls(
    content: str,
    valid_names: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """Extract tool calls emitted as raw or markdown JSON in the content string.

    Handles single JSON objects, newline-delimited JSON objects, arrays of JSON objects,
    and markdown code-fenced json blocks using streaming JSONDecoder.raw_decode.
    """
    if not content or "{" not in content:
        return []

    if valid_names is None:
        valid_names = {t.name for t in registry.list_tools()}

    calls: List[Dict[str, Any]] = []
    decoder = json.JSONDecoder()
    idx = 0
    length = len(content)

    while idx < length:
        idx = content.find("{", idx)
        if idx == -1:
            break
        try:
            obj, end_idx = decoder.raw_decode(content[idx:])
            idx += end_idx
            if isinstance(obj, dict):
                name = obj.get("name") or obj.get("tool")
                if not name and isinstance(obj.get("function"), dict):
                    name = obj.get("function", {}).get("name")
                elif not name and isinstance(obj.get("function"), str):
                    name = obj.get("function")

                args = obj.get("arguments") or obj.get("args") or obj.get("parameters")
                if args is None and isinstance(obj.get("function"), dict):
                    args = obj.get("function", {}).get("arguments") or obj.get("function", {}).get("parameters")
                if args is None:
                    args = {}

                if isinstance(name, str) and name in valid_names:
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    calls.append({
                        "id": f"call_fallback_{len(calls)}",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": args,
                        },
                    })
        except Exception:
            idx += 1

    return calls
