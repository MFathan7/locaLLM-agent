"""Asynchronous background memory extractor scoped to workspace turns."""

import json
import logging
import re
import threading
from typing import Any, Dict, Optional

from locallm.core.workspace_memory import WorkspaceMemoryManager

logger = logging.getLogger(__name__)

def _is_trivial_turn(user_prompt: str, assistant_response: str) -> bool:
    """Filter out empty, whitespace-only, or system error turns prior to LLM extraction.

    Semantic relevance is determined autonomously by the LLM in any language,
    without brittle hardcoded keyword dictionaries.
    """
    clean_user = (user_prompt or "").strip()
    clean_asst = (assistant_response or "").strip()
    if not clean_user or not clean_asst:
        return True

    # Filter out short bracketed system error notifications
    if clean_asst.startswith("[") and clean_asst.endswith("]") and len(clean_asst) < 40:
        return True

    return False


def _extract_worker(
    workspace_name: str,
    client: Any,
    model: str,
    user_prompt: str,
    assistant_response: str,
    session_id: Optional[str] = None,
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
            "Analyze the conversation turn below in any language and extract any durable, permanent facts about the user's specific project, "
            "activities, purchases, dates, quantities, decisions, environment, configuration, or preferences.\n\n"
            "Guidelines:\n"
            "- Ignore casual greetings, reactions, pleasantries, general knowledge, or transient debugging questions.\n"
            "- Extract ONLY durable facts specific to this workspace.\n"
            "- If NO durable facts are found, reply strictly with: NONE\n"
            "- If facts ARE found, reply ONLY with a valid JSON object in this exact format:\n"
            '{"facts": {"snake_case_key": "concise factual statement"}}\n\n'
            f"Turn:\nUser: {user_prompt.strip()}\nAssistant: {assistant_response[:600].strip()}\n"
        )

        messages = [
            {"role": "user", "content": extraction_prompt}
        ]

        raw_result = ""
        if hasattr(client, "chat"):
            try:
                resp = client.chat(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                    num_ctx=2048,
                )
                raw_result = resp.get("content", "") if isinstance(resp, dict) else str(resp)
            except TypeError:
                resp = client.chat(
                    model=model,
                    messages=messages,
                    temperature=0.1,
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

        if not raw_result:
            return

        # 1. Clean reasoning tokens (<think>...</think>) before analyzing response
        cleaned_text = re.sub(
            r"<(?:think|thought)>[\s\S]*?</(?:think|thought)>",
            "",
            raw_result,
            flags=re.IGNORECASE,
        ).strip()
        cleaned_text = re.sub(
            r"<(?:think|thought)>[\s\S]*$",
            "",
            cleaned_text,
            flags=re.IGNORECASE,
        ).strip()

        # 2. Check if clean payload is empty or explicitly NONE
        clean_lower = cleaned_text.lower().strip()
        if not clean_lower or clean_lower == "none" or clean_lower.startswith("none"):
            return

        # 3. Locate JSON block in cleaned text or raw result
        json_match = re.search(r"\{[\s\S]*\}", cleaned_text) or re.search(r"\{[\s\S]*\}", raw_result)
        if not json_match:
            return

        parsed = json.loads(json_match.group(0))
        facts = parsed.get("facts", {})
        if isinstance(facts, dict):
            for k, v in facts.items():
                if k and v:
                    clean_k = str(k).strip()
                    clean_v = str(v).strip()
                    clean_v = re.sub(r"<(?:think|thought)>[\s\S]*?</(?:think|thought)>", "", clean_v, flags=re.IGNORECASE).strip()
                    if clean_k and clean_v:
                        mgr.set_fact(clean_k, clean_v, session_id=session_id)
                        logger.info(
                            "Auto-extracted workspace fact for '%s': %s -> %s (session: %s)",
                            workspace_name,
                            clean_k,
                            clean_v,
                            session_id or "untracked",
                        )
    except Exception as exc:
        logger.debug("Auto-memory extraction skipped: %s", exc)


def extract_workspace_memory_async(
    workspace_name: str,
    client: Any,
    model: str,
    user_prompt: str,
    assistant_response: str,
    session_id: Optional[str] = None,
) -> None:
    """Dispatch background thread for automatic episodic memory extraction without blocking response."""
    if not workspace_name or not client or not user_prompt:
        return

    thread = threading.Thread(
        target=_extract_worker,
        args=(workspace_name, client, model, user_prompt, assistant_response, session_id),
        daemon=True,
        name=f"auto-mem-{workspace_name}",
    )
    thread.start()
