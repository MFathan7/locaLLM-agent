"""Conversation memory and message history manager."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConversationMemory:
    """Stores and formats multi-turn chat history."""

    def __init__(self, system_prompt: Optional[str] = None):
        self.system_prompt = system_prompt
        self.history: List[Dict[str, Any]] = []
        self.last_stats: Dict[str, Any] = {}

    def update_stats(self, stats: Dict[str, Any]) -> None:
        """Store the latest inference evaluation statistics."""
        if stats:
            self.last_stats = dict(stats)

    def get_context_usage(self, default_limit: int = 8192) -> Dict[str, Any]:
        """Compute cumulative token context metrics for active conversation."""
        prompt_tok = self.last_stats.get("prompt_eval_count", 0)
        eval_tok = self.last_stats.get("eval_count", 0)
        total_tok = prompt_tok + eval_tok
        if total_tok == 0:
            char_count = sum(len(str(m.get("content", ""))) for m in self.get_messages())
            total_tok = max(0, char_count // 4)
        limit = max(default_limit, total_tok)
        pct = (total_tok / limit * 100) if limit > 0 else 0.0
        eval_dur_ns = self.last_stats.get("eval_duration", 0)
        tps = (eval_tok / (eval_dur_ns / 1e9)) if eval_dur_ns > 0 else 0.0
        return {
            "total_tokens": total_tok,
            "limit": limit,
            "percentage": pct,
            "tps": tps,
        }

    def set_system_prompt(self, prompt: str) -> None:
        """Update system instruction prompt."""
        self.system_prompt = prompt

    def add_user_message(self, content: str, images: Optional[List[str]] = None) -> None:
        """Append user message to history with optional base64 image data."""
        msg: Dict[str, Any] = {"role": "user", "content": content}
        if images:
            msg["images"] = images
        self.history.append(msg)

    def add_assistant_message(self, content: str) -> None:
        """Append assistant response to history."""
        self.history.append({"role": "assistant", "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        """Return full messages list including active system prompt."""
        messages: List[Dict[str, str]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(self.history)
        return messages

    def clear(self) -> None:
        """Reset conversation messages while retaining system prompt."""
        self.history.clear()

    def to_dict(self, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Convert memory state and history to a dictionary."""
        data: Dict[str, Any] = {
            "system_prompt": self.system_prompt,
            "history": self.history,
        }
        if metadata:
            data["metadata"] = metadata
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemory":
        """Reconstruct ConversationMemory instance from dictionary."""
        mem = cls(system_prompt=data.get("system_prompt"))
        mem.history = list(data.get("history", []))
        return mem

    def save_to_json(self, destination: Path, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Save full memory state with metadata to a JSON file."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_dict(metadata=metadata)
        with open(destination, "w", encoding="utf-8", errors="replace") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)

    def load_from_json(self, source: Path) -> None:
        """Load conversation state and history from a JSON file."""
        if not source.is_file():
            return
        with open(source, "r", encoding="utf-8", errors="replace") as file:
            data = json.load(file)
        if isinstance(data, dict):
            if "system_prompt" in data and data["system_prompt"] is not None:
                self.system_prompt = data["system_prompt"]
            self.history = list(data.get("history", []))
        elif isinstance(data, list):
            # Legacy export format: list of messages
            self.history = [msg for msg in data if msg.get("role") != "system"]

    def export_to_json(self, destination: Path) -> None:
        """Export raw message history to a JSON file."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        with open(destination, "w", encoding="utf-8", errors="replace") as file:
            json.dump(self.get_messages(), file, indent=2, ensure_ascii=False)

