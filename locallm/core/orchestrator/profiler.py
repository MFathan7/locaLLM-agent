"""Dynamic capability profiler and model dispatch selector for local LLMs."""

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional


@dataclass
class ModelProfile:
    """Dynamic capability scores for an installed local model."""

    name: str
    parameter_size: float
    context_length: int
    family: str
    coding_score: float
    tool_score: float
    reasoning_score: float
    vision_score: float
    speed_score: float


def profile_model(raw_model: Any) -> ModelProfile:
    """Compute multidimensional capability scores from model metadata and naming taxonomy."""
    name = raw_model.get("name", "") if isinstance(raw_model, dict) else str(raw_model)
    details = raw_model.get("details", {}) if isinstance(raw_model, dict) else {}

    family = str(details.get("family", "")).lower()
    raw_families = details.get("families", []) or []
    families = [str(f).lower() for f in raw_families if f]
    ctx = int(details.get("context_length") or 8192)

    p_size_str = str(details.get("parameter_size", "")).strip()
    p_match = re.search(r"([\d.]+)", p_size_str) if p_size_str else None
    params = float(p_match.group(1)) if p_match and float(p_match.group(1)) > 0 else 0.0

    if params <= 0.0:
        name_match = re.search(r"(\d+(?:\.\d+)?)[bB]\b", name)
        params = float(name_match.group(1)) if name_match else 7.0

    lower = name.lower()

    # 1. Coding Capability
    coding = 0.0
    if any(k in lower for k in ("coder", "code", "starcoder", "dev", "deepseek-coder", "codestral")):
        coding += 4.5
    if any(k in lower or k in family for k in ("qwen2", "deepseek")):
        coding += 1.5
    coding += min(params * 0.1, 2.0)

    # 2. Tool Calling and Agentic Steering
    tools = 0.0
    if any(k in lower for k in ("hermes", "function", "agent", "tool")):
        tools += 4.0
    if any(k in lower or k in family for k in ("qwen", "qwen3", "qwen2")):
        tools += 3.5
    if any(k in lower or k in family for k in ("llama", "mistral", "gemma", "glm")):
        tools += 2.5
    if ctx >= 120000:
        tools += 1.0
    tools += min(params * 0.1, 2.0)

    # 3. Vision & Multimodal
    vision = 0.0
    if "clip" in families or any(k in lower for k in ("vision", "-v-", "-v:", "vl", "llava")):
        vision += 5.0

    # 4. Reasoning & Depth
    reasoning = 0.0
    if any(k in lower for k in ("r1", "qwq", "thinking", "reason")):
        reasoning += 5.0
    if any(k in lower or k in family for k in ("qwen3", "glm4", "gemma4", "llama3")):
        reasoning += 2.5
    reasoning += min(params * 0.2, 4.0)

    # 5. Speed & Latency
    speed = max(0.0, 10.0 - params * 0.6)
    if any(k in lower for k in ("flash", "mini", "turbo", "fast")):
        speed += 2.5

    return ModelProfile(
        name=name,
        parameter_size=params,
        context_length=ctx,
        family=family,
        coding_score=round(coding, 2),
        tool_score=round(tools, 2),
        reasoning_score=round(reasoning, 2),
        vision_score=round(vision, 2),
        speed_score=round(speed, 2),
    )


def get_installed_profiles(client: Any) -> List[ModelProfile]:
    """Retrieve and profile all models currently available in local engine."""
    raw_models: List[Any] = []
    if hasattr(client, "list_models"):
        try:
            raw_models = client.list_models() or []
        except Exception:
            raw_models = []

    profiles: List[ModelProfile] = []
    for m in raw_models:
        p = profile_model(m)
        if p.name:
            profiles.append(p)
    return profiles


def get_best_model_for_role(role: str, client: Any, config: Any) -> str:
    """Dynamically select the highest-scoring installed model for a specific agent role."""
    fallback = getattr(config, "default_model", "qwen3.5:9b")
    if fallback.lower() == "auto":
        fallback = getattr(config, "ollama_model", "qwen3.5:9b")

    profiles = get_installed_profiles(client)
    if not profiles:
        return fallback

    role_key = role.lower().strip()

    def _score(p: ModelProfile) -> float:
        if role_key == "coder":
            return p.coding_score * 0.7 + p.tool_score * 0.3
        elif role_key == "supervisor":
            return p.tool_score * 0.6 + p.reasoning_score * 0.4
        elif role_key == "researcher":
            return p.reasoning_score * 0.5 + p.tool_score * 0.5
        elif role_key == "auditor":
            return p.tool_score * 0.6 + p.speed_score * 0.4
        elif role_key == "fast":
            return p.speed_score
        elif role_key == "reasoning":
            return p.reasoning_score
        else:
            return p.tool_score * 0.5 + p.reasoning_score * 0.5

    sorted_profiles = sorted(profiles, key=_score, reverse=True)
    return sorted_profiles[0].name
