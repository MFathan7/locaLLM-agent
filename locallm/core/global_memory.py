"""Global persistent memory manager across workspaces for locaLLM."""

import json
import logging
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_FILE = Path.home() / ".locallm" / "global_memory.json"

DEFAULT_MEMORY_STRUCTURE: Dict[str, Any] = {
    "user_profile": {},
    "communication_rules": [],
    "facts": {},
}


class GlobalMemoryManager:
    """Manages persistent global user preferences, profile, rules, and facts across workspaces."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        if storage_path:
            self.storage_path = Path(storage_path).expanduser().resolve()
        else:
            self.storage_path = DEFAULT_MEMORY_FILE

        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure parent directory exists and default memory file is created if missing."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.storage_path.exists():
                self.save(dict(DEFAULT_MEMORY_STRUCTURE))
        except Exception as exc:
            logger.warning("Failed to initialize global memory storage at %s: %s", self.storage_path, exc)

    def load(self) -> Dict[str, Any]:
        """Safely load global memory JSON with graceful fallback on corruption or errors."""
        if not self.storage_path.is_file():
            return {
                "user_profile": {},
                "communication_rules": [],
                "facts": {},
            }

        try:
            with open(self.storage_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                logger.warning(
                    "Global memory root is not a dict at %s, resetting to default structure.",
                    self.storage_path,
                )
                return {
                    "user_profile": {},
                    "communication_rules": [],
                    "facts": {},
                }

            # Normalize structure ensuring all required keys and valid types exist
            user_profile = data.get("user_profile")
            if not isinstance(user_profile, dict):
                user_profile = {}

            communication_rules = data.get("communication_rules")
            if not isinstance(communication_rules, list):
                communication_rules = []
            else:
                # Filter to non-empty string rules preserving uniqueness
                seen_rules = set()
                cleaned_rules: List[str] = []
                for r in communication_rules:
                    rule_str = str(r).strip()
                    if rule_str and rule_str not in seen_rules:
                        seen_rules.add(rule_str)
                        cleaned_rules.append(rule_str)
                communication_rules = cleaned_rules

            facts = data.get("facts")
            if not isinstance(facts, dict):
                facts = {}

            return {
                "user_profile": user_profile,
                "communication_rules": communication_rules,
                "facts": facts,
            }
        except (json.JSONDecodeError, OSError, UnicodeError, Exception) as exc:
            logger.warning(
                "Failed to read global memory from %s (%s). Using default structure.",
                self.storage_path,
                exc,
            )
            return {
                "user_profile": {},
                "communication_rules": [],
                "facts": {},
            }

    def save(self, data: Dict[str, Any]) -> bool:
        """Atomically write memory state to disk to prevent data corruption."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Ensure valid normalized dictionary
            normalized: Dict[str, Any] = {
                "user_profile": (
                    data.get("user_profile", {})
                    if isinstance(data.get("user_profile"), dict)
                    else {}
                ),
                "communication_rules": (
                    data.get("communication_rules", [])
                    if isinstance(data.get("communication_rules"), list)
                    else []
                ),
                "facts": (
                    data.get("facts", {})
                    if isinstance(data.get("facts"), dict)
                    else {}
                ),
            }

            parent_dir = self.storage_path.parent
            temp_file = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=parent_dir,
                delete=False,
                prefix="global_memory_",
                suffix=".tmp",
            )
            temp_path = Path(temp_file.name)
            try:
                json.dump(normalized, temp_file, indent=2, ensure_ascii=False)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_file.close()

                # Atomic replace
                temp_path.replace(self.storage_path)
                return True
            except Exception:
                temp_file.close()
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
                raise
        except Exception as exc:
            logger.error("Failed to atomic-save global memory to %s: %s", self.storage_path, exc)
            return False

    def set_fact(self, category: str, key: str, value: Any) -> bool:
        """Add or update an item in global memory under the specified category."""
        data = self.load()
        cat = (category or "").strip().lower()

        if cat in ("communication_rules", "rules"):
            # Communication rules is a list of strings
            rule_text = ""
            if value is not None and str(value).strip():
                rule_text = str(value).strip()
            elif key and str(key).strip():
                rule_text = str(key).strip()

            if not rule_text:
                return False

            rules: List[str] = data.setdefault("communication_rules", [])
            # Avoid duplicate rules
            if rule_text not in rules:
                rules.append(rule_text)
            return self.save(data)

        elif cat in ("user_profile", "profile"):
            clean_key = str(key).strip() if key else ""
            if not clean_key:
                return False
            data.setdefault("user_profile", {})[clean_key] = value
            return self.save(data)

        elif cat in ("facts", "fact"):
            clean_key = str(key).strip() if key else ""
            if not clean_key:
                return False
            data.setdefault("facts", {})[clean_key] = value
            return self.save(data)

        else:
            # Fallback for unrecognized categories -> store in facts
            clean_key = str(key).strip() if key else ""
            if not clean_key:
                return False
            data.setdefault("facts", {})[f"{cat}_{clean_key}"] = value
            return self.save(data)

    def delete_fact(self, category: str, key: str) -> bool:
        """Remove an item from global memory."""
        data = self.load()
        cat = (category or "").strip().lower()
        clean_key = str(key).strip() if key else ""

        if cat in ("communication_rules", "rules"):
            rules: List[str] = data.get("communication_rules", [])
            initial_len = len(rules)
            data["communication_rules"] = [
                r for r in rules if r != clean_key and r.lower() != clean_key.lower()
            ]
            if len(data["communication_rules"]) < initial_len:
                return self.save(data)
            return False

        elif cat in ("user_profile", "profile"):
            profile = data.get("user_profile", {})
            if clean_key in profile:
                del profile[clean_key]
                return self.save(data)
            return False

        elif cat in ("facts", "fact"):
            facts = data.get("facts", {})
            if clean_key in facts:
                del facts[clean_key]
                return self.save(data)
            return False

        else:
            facts = data.get("facts", {})
            composite_key = f"{cat}_{clean_key}"
            if composite_key in facts:
                del facts[composite_key]
                return self.save(data)
            return False

    def build_system_context(self) -> str:
        """Format global memory into compact supplementary system context.

        Format:
        <global_user_memory>
        [User Profile]
        - key: value

        [Rules]
        - rule

        [Facts]
        - key: value
        </global_user_memory>

        Returns empty string if all sections are empty to conserve tokens.
        """
        data = self.load()
        user_profile = data.get("user_profile", {})
        communication_rules = data.get("communication_rules", [])
        facts = data.get("facts", {})

        sections: List[str] = []

        if user_profile and isinstance(user_profile, dict):
            profile_lines: List[str] = ["[User Profile]"]
            for k, v in sorted(user_profile.items()):
                clean_v = str(v).strip()
                if clean_v:
                    profile_lines.append(f"- {k}: {clean_v}")
            if len(profile_lines) > 1:
                sections.append("\n".join(profile_lines))

        if communication_rules and isinstance(communication_rules, list):
            rule_lines: List[str] = ["[Rules]"]
            for r in communication_rules:
                clean_r = str(r).strip()
                if clean_r:
                    rule_lines.append(f"- {clean_r}")
            if len(rule_lines) > 1:
                sections.append("\n".join(rule_lines))

        if facts and isinstance(facts, dict):
            fact_lines: List[str] = ["[Facts]"]
            for k, v in sorted(facts.items()):
                clean_v = str(v).strip()
                if clean_v:
                    fact_lines.append(f"- {k}: {clean_v}")
            if len(fact_lines) > 1:
                sections.append("\n".join(fact_lines))

        if not sections:
            return ""

        body = "\n\n".join(sections)
        return f"<global_user_memory>\n{body}\n</global_user_memory>"
