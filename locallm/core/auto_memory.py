"""Asynchronous background memory extractor scoped to workspace turns."""

import json
import logging
import re
import threading
from typing import Any, Dict, Optional

from locallm.core.workspace_memory import WorkspaceMemoryManager

logger = logging.getLogger(__name__)

TRIVIAL_PROMPT_PATTERNS = [
    r"^(?:halo|hi|hello|hey|tes|test|p|ping|ok|oke|siap|makasih|terima kasih|thanks|thank you)[\s.!?,]*$",
    r"^(?:bagus|mantap|keren|sip|lanjut|clear|reset)[\s.!?,]*$",
]


def _is_trivial_turn(user_prompt: str, assistant_response: str) -> bool:
    """Filter out casual conversation, short greetings, and transient queries from extraction."""
    clean_user = user_prompt.strip().lower()
    if len(clean_user) < 8:
        return True

    for pat in TRIVIAL_PROMPT_PATTERNS:
        if re.match(pat, clean_user, re.IGNORECASE):
            return True

    # If assistant response is an error notice
    if assistant_response.startswith("[Gagal") or assistant_response.startswith("[Kendala"):
        return True

    return False


def _extract_worker(
    workspace_name: str,
    client: Any,
    model: str,
    user_prompt: str,
    assistant_response: str,
) -> None:
    """Worker function executed in background thread."""
    try:
        mgr = WorkspaceMemoryManager(workspace_name)
        if not mgr.is_auto_memory_enabled():
            return

        if _is_trivial_turn(user_prompt, assistant_response):
            return

        # Prepare extraction instruction
        extraction_prompt = (
            f"You are an episodic memory extractor for the active workspace '{workspace_name}'.\n"
            "Analyze the conversation turn below and extract any durable, permanent facts about the user's specific project, "
            "activities, purchases, dates, quantities, decisions, environment, or configuration.\n\n"
            "Guidelines:\n"
            "- Ignore casual chat, greetings, general knowledge, or transient debugging questions.\n"
            "- Extract ONLY durable facts specific to this workspace.\n"
            "- If NO durable facts are found, reply exactly with: NONE\n"
            "- If facts ARE found, reply ONLY with a valid JSON object in this exact format:\n"
            '{"facts": {"snake_case_key": "concise factual statement"}}\n\n'
            f"Turn:\nUser: {user_prompt.strip()}\nAssistant: {assistant_response[:600].strip()}\n"
        )

        messages = [
            {"role": "user", "content": extraction_prompt}
        ]

        raw_result = ""
        if hasattr(client, "chat"):
            resp = client.chat(
                model=model,
                messages=messages,
                temperature=0.1,
                num_ctx=2048,
            )
            raw_result = resp.get("content", "") if isinstance(resp, dict) else str(resp)
        elif hasattr(client, "chat_turn"):
            resp = client.chat_turn(
                model=model,
                messages=messages,
                temperature=0.1,
                num_ctx=2048,
            )
            raw_result = resp.get("content", "") if isinstance(resp, dict) else str(resp)

        if not raw_result or "none" in raw_result.strip().lower():
            return

        # Extract JSON from output
        json_match = re.search(r"\{[\s\S]*\}", raw_result)
        if not json_match:
            return

        parsed = json.loads(json_match.group(0))
        facts = parsed.get("facts", {})
        if isinstance(facts, dict):
            for k, v in facts.items():
                if k and v:
                    clean_k = str(k).strip()
                    clean_v = str(v).strip()
                    # Strip think tags if any
                    clean_v = re.sub(r"<(?:think|thought)>[\s\S]*?</(?:think|thought)>", "", clean_v).strip()
                    if clean_k and clean_v:
                        mgr.set_fact(clean_k, clean_v)
                        logger.info(
                            "Auto-extracted workspace fact for '%s': %s -> %s",
                            workspace_name,
                            clean_k,
                            clean_v,
                        )
    except Exception as exc:
        logger.debug("Auto-memory extraction skipped: %s", exc)


def extract_workspace_memory_async(
    workspace_name: str,
    client: Any,
    model: str,
    user_prompt: str,
    assistant_response: str,
) -> None:
    """Dispatch background thread for automatic episodic memory extraction without blocking response."""
    if not workspace_name or not client or not user_prompt:
        return

    thread = threading.Thread(
        target=_extract_worker,
        args=(workspace_name, client, model, user_prompt, assistant_response),
        daemon=True,
        name=f"auto-mem-{workspace_name}",
    )
    thread.start()
