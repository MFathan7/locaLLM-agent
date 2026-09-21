"""Intelligent Semantic Model Router for dynamic, capability- and complexity-aware model dispatch."""

from enum import Enum
import re
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from locallm.config import LocaLLMConfig
from locallm.core.hardware import calculate_vram_breakdown


class TaskType(str, Enum):
    """Categorized intent of a user prompt."""

    CODING = "CODING"
    REASONING = "REASONING"
    VISION = "VISION"
    TOOLS = "TOOLS"
    FAST_CHAT = "FAST_CHAT"


class TaskTier(str, Enum):
    """Execution tier: Fast direct response vs Deep reasoning."""

    FAST = "FAST"
    DEEP_REASONING = "DEEP_REASONING"


class ModelRouteResult(NamedTuple):
    """Container for model routing decision and metadata."""

    selected_model: str
    task_type: TaskType
    tier: TaskTier
    reason: str
    is_swapped: bool


# Deep reasoning detection signals (causal, mathematical, architectural, formal logic)
REASONING_PATTERNS = [
    r"\b(prove|proof|bukti|buktikan|step[- ]by[- ]step|calculate|hitung|derivation|theorem|puzzle|riddle|syllogism)\b",
    r"\b(why does|how come|root cause|underlying cause|trade[- ]off|compare and contrast)\b",
    r"\b(time complexity|space complexity|big[- ]o|algorithm analysis|asymptotic|mathematical)\b",
    r"\b(architecture trade-off|system design trade-off|deep dive|explain in detail why)\b",
    r"\b(analyze the logic|deduce|deductive|inductive|logical flaw)\b",
]

# Coding specialist detection signals
CODING_PATTERNS = [
    r"```[a-zA-Z0-9_\-+]*\n[\s\S]*?```",  # Markdown code blocks
    r"`[^`]{4,}`",                          # Inline code identifiers
    r"\b(def|class|async def|return|import|from\s+\w+\s+import|function|const|let|var)\b",
    r"\b(syntax error|traceback|stacktrace|exception|null pointer|segfault|debug this)\b",
    r"\b(refactor|unit test|mock|pytest|unittest|sql query|regex|git diff|pull request)\b",
    r"\b(\.py|\.js|\.ts|\.go|\.rs|\.cpp|\.java|\.json|\.html|\.css|\.sql)\b",
]

# Tool, filesystem, terminal, and schema execution signals
TOOL_PATTERNS = [
    # Structural filesystem path detection (Windows drive letters, POSIX paths, relative paths)
    r"\b[a-zA-Z]:[/\\][^\s*?\"<>|]+",
    r"(?:^|\s)(?:~|/|\./|\.\./)[a-zA-Z0-9_\-./]+",
    # Universal file & directory operations
    r"\b(create|write|read|save|list|generate|make|build|dump|output|export|mkdir|touch)\b.*?\b(file|files|folder|dir|directory|project|script|code)\b",
    r"\b(buat|buatkan|bikin|tulis|baca|simpan)\b.*?\b(file|filenya|folder|direktori|berkas|skrip|script|code|project)\b",
    r"\b(write_file|create_directory|read_file|list_directory)\b",
    # Terminal, system commands, and web/API fetching
    r"\b(run|execute|jalankan)\s+(?:command|cmd|terminal|powershell|bash|shell|script)\b",
    r"\b(curl|wget|fetch|download|unduh|ping|http[s]?://)\b",
    r"\b(weather|temperature|forecast|suhu|cuaca)\b",
    r"\b(tool call|function calling|schema json|json schema|trigger_\w+|execute tool)\b",
]

# Fast / Direct factual signals
FAST_PATTERNS = [
    r"^(hi|hello|halo|hey|p|tes|test|ping|good morning|good afternoon|good evening|selamat pagi|siang|sore|malam)[.!?]*$",
    r"\b(what is|who is|artinya|terjemahkan|translate|bullet points?|summarize|ringkas|rangkum|singkatkan)\b",
    r"\b(in simple terms|secara sederhana|analogi|explain simply)\b",
]


def classify_prompt(
    prompt: str,
    has_image: bool = False,
    is_agent_task: bool = False,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[TaskType, TaskTier, str]:
    """Classify prompt into task type and execution tier (Fast vs Deep Reasoning)."""
    clean = prompt.strip()

    if has_image:
        return TaskType.VISION, TaskTier.FAST, "Visual input detected"

    if is_agent_task:
        return TaskType.TOOLS, TaskTier.DEEP_REASONING, "Autonomous agent tool execution"

    # 0. Multi-turn context awareness: check if this is an ongoing technical follow-up action
    if history and len(history) >= 2:
        last_assistant_content = ""
        for msg in reversed(history):
            if msg.get("role") == "assistant" and msg.get("content"):
                last_assistant_content = msg.get("content", "")
                break

        # Check if previous assistant turn contained code blocks, file trees, or architecture
        had_code_or_files = (
            "```" in last_assistant_content
            or "├──" in last_assistant_content
            or "└──" in last_assistant_content
            or bool(re.search(r"\b(def|class|import|function|const|folder|directory|architecture)\b", last_assistant_content, re.IGNORECASE))
        )

        if had_code_or_files:
            is_action_followup = bool(
                re.search(r"\b(filenya|kodenya|buatkan|simpan|terapkan|implementasikan|lanjutkan|bikin)\b", clean, re.IGNORECASE)
                or re.search(r"\b(create|write|save|implement|generate|put|store|run|execute|continue|proceed|dump)\b", clean, re.IGNORECASE)
                or re.search(r"\b(it|them|this|these|files?|folders?|all|code|script)\b", clean, re.IGNORECASE)
                or re.search(r"[a-zA-Z]:[/\\]", clean)
                or re.search(r"(?:^|\s)(?:~|/|\./)", clean)
            )
            if is_action_followup:
                return TaskType.TOOLS, TaskTier.DEEP_REASONING, "Technical follow-up action to previous code/architecture"

    # 1. Tool intent check (filesystem paths, file creation, command, web, weather)
    for pat in TOOL_PATTERNS:
        if re.search(pat, clean, re.IGNORECASE):
            return TaskType.TOOLS, TaskTier.DEEP_REASONING, "System tool / schema extraction intent"

    # 2. Coding check
    coding_score = 0
    for pat in CODING_PATTERNS:
        if re.search(pat, clean, re.IGNORECASE):
            coding_score += 2

    if coding_score >= 2:
        # If code has complex debugging signals, elevate to Deep Reasoning
        if "traceback" in clean.lower() or "why" in clean.lower() or "debug" in clean.lower():
            return TaskType.CODING, TaskTier.DEEP_REASONING, "Complex code debugging / analysis intent"
        return TaskType.CODING, TaskTier.FAST, "Software development / coding intent"

    # 3. Deep Reasoning check
    reasoning_score = 0
    for pat in REASONING_PATTERNS:
        if re.search(pat, clean, re.IGNORECASE):
            reasoning_score += 2
    if len(clean) > 300 and ("?" in clean or ":" in clean):
        reasoning_score += 1

    if reasoning_score >= 2:
        return TaskType.REASONING, TaskTier.DEEP_REASONING, "Deep reasoning / logical analysis intent"

    # 4. Fast Chat check
    for pat in FAST_PATTERNS:
        if re.search(pat, clean, re.IGNORECASE):
            return TaskType.FAST_CHAT, TaskTier.FAST, "Quick conversational / factual intent"

    # Conversational / analogy / simple explanatory checks
    if any(k in clean.lower() for k in ("santai", "analogi", "simpel", "sederhana", "ringkas")):
        return TaskType.FAST_CHAT, TaskTier.FAST, "Conversational / explanatory prompt"

    # Default general chat
    if len(clean.split()) <= 20:
        return TaskType.FAST_CHAT, TaskTier.FAST, "Direct conversational prompt"
    return TaskType.REASONING, TaskTier.DEEP_REASONING, "Comprehensive multi-step inquiry"


def route_prompt(
    prompt: str,
    config: LocaLLMConfig,
    client: Any,
    has_image: bool = False,
    is_agent_task: bool = False,
    history: Optional[List[Dict[str, Any]]] = None,
) -> ModelRouteResult:
    """Intelligently route prompt to optimal local model with sticky anti-thrashing safeguards."""
    task_type, tier, reason_prefix = classify_prompt(
        prompt, has_image=has_image, is_agent_task=is_agent_task, history=history
    )

    # Fetch available models from client
    raw_models: List[Dict[str, Any]] = []
    if hasattr(client, "list_models"):
        try:
            raw_models = client.list_models() or []
        except Exception:
            raw_models = []

    model_names: List[str] = []
    model_size_map: Dict[str, int] = {}
    for m in raw_models:
        name = m.get("name") or m.get("id")
        if name and name not in model_names:
            model_names.append(name)
            model_size_map[name] = m.get("size", 0)

    # Determine baseline fallback model
    fallback_model = (
        config.ollama_model
        if config.ollama_model and config.ollama_model.lower() != "auto"
        else (model_names[0] if model_names else "gemma4:12b")
    )

    if not model_names:
        return ModelRouteResult(
            selected_model=fallback_model,
            task_type=task_type,
            tier=tier,
            reason=f"{reason_prefix} -> Fallback default: {fallback_model}",
            is_swapped=False,
        )

    # Inspect currently loaded model in GPU memory (sticky candidate)
    loaded_models: List[str] = []
    if hasattr(client, "get_loaded_models"):
        try:
            loaded_models = client.get_loaded_models() or []
        except Exception:
            loaded_models = []
    current_model = loaded_models[0] if loaded_models else fallback_model

    # Categorize available models by specialty
    reasoning_models: List[str] = []
    coder_models: List[str] = []
    vision_models: List[str] = []
    tool_models: List[str] = []
    fast_models: List[str] = []

    for name in model_names:
        lower = name.lower()
        features: List[str] = []
        if hasattr(client, "get_model_features"):
            try:
                features = client.get_model_features(name)
            except Exception:
                features = []

        if "Reasoning" in features or any(k in lower for k in ("r1", "qwq", "thinking", "reason")):
            reasoning_models.append(name)
        if any(k in lower for k in ("coder", "code", "dev", "starcoder")):
            coder_models.append(name)
        if "Vision" in features or any(k in lower for k in ("vision", "vl", "llava")):
            vision_models.append(name)
        if "Tools" in features or any(k in lower for k in ("tool", "hermes", "function", "gemma", "llama", "qwen", "mistral")):
            tool_models.append(name)
        if "Reasoning" not in features or any(k in lower for k in ("3b", "7b", "8b", "mini", "flash", "hermes")):
            fast_models.append(name)

    # Generic, capability- and capacity-based priority sorting (descending by size/weights)
    reasoning_models.sort(key=lambda m: (0 if any(k in m.lower() for k in ("r1", "qwq", "qwen")) else 1, -model_size_map.get(m, 0)))
    coder_models.sort(key=lambda m: -model_size_map.get(m, 0))
    tool_models.sort(key=lambda m: -model_size_map.get(m, 0))
    fast_models.sort(key=lambda m: (0 if any(k in m.lower() for k in ("hermes", "mini", "3b", "7b", "8b")) else 1, model_size_map.get(m, 0)))

    selected = current_model
    final_reason = ""
    is_swapped = False

    # Selection Strategy with Sticky Routing (Anti-Swap)
    if task_type == TaskType.VISION:
        if current_model in vision_models:
            selected = current_model
            final_reason = f"{reason_prefix} -> Retained active Vision model: {selected}"
        elif vision_models:
            selected = vision_models[0]
            final_reason = f"{reason_prefix} -> Dispatched to Vision model: {selected}"
        else:
            selected = current_model
            final_reason = f"{reason_prefix} -> No dedicated Vision model, retained: {selected}"

    elif task_type == TaskType.REASONING:
        # For deep reasoning, prefer dedicated reasoning engine if available and not currently active
        if reasoning_models and current_model not in reasoning_models:
            selected = reasoning_models[0]
            final_reason = f"{reason_prefix} -> Dispatched to Reasoning specialist: {selected} (Deep Thinking)"
        elif reasoning_models and any(k in reasoning_models[0].lower() for k in ("r1", "qwq", "qwen")) and not any(k in current_model.lower() for k in ("r1", "qwq", "qwen")):
            selected = reasoning_models[0]
            final_reason = f"{reason_prefix} -> Dispatched to Primary Reasoning specialist: {selected}"
        else:
            selected = current_model
            final_reason = f"{reason_prefix} -> Retained active engine: {selected} (Deep Thinking)"

    elif task_type == TaskType.CODING:
        # If current model is already coder or capable generalist, stick with it
        if current_model in coder_models:
            selected = current_model
            final_reason = f"{reason_prefix} -> Retained active Coder: {selected}"
        elif coder_models:
            selected = coder_models[0]
            final_reason = f"{reason_prefix} -> Dispatched to Coding specialist: {selected}"
        else:
            selected = current_model
            final_reason = f"{reason_prefix} -> Generalist handling code: {selected}"

    elif task_type == TaskType.TOOLS:
        # If currently loaded model is a small fast model and a higher-capacity tool specialist is available,
        # elevate to the primary tool specialist for complex schema and execution reliability
        should_elevate = (
            tool_models
            and tool_models[0] != current_model
            and (current_model in fast_models or model_size_map.get(tool_models[0], 0) > model_size_map.get(current_model, 0))
        )
        if should_elevate:
            selected = tool_models[0]
            final_reason = f"{reason_prefix} -> Dispatched to Primary Tool specialist: {selected}"
        elif current_model in tool_models:
            selected = current_model
            final_reason = f"{reason_prefix} -> Retained Tool-capable model: {selected}"
        elif tool_models:
            selected = tool_models[0]
            final_reason = f"{reason_prefix} -> Dispatched to Tool specialist: {selected}"
        else:
            selected = current_model
            final_reason = f"{reason_prefix} -> Retained active model for tools: {selected}"

    else:  # FAST_CHAT
        # If current model is a heavy reasoning engine with CoT thinking overhead,
        # dispatch to fast direct model for zero-thinking-overhead response
        current_features: List[str] = []
        if hasattr(client, "get_model_features"):
            try:
                current_features = client.get_model_features(current_model)
            except Exception:
                current_features = []
        is_current_reasoning = "Reasoning" in current_features or any(k in current_model.lower() for k in ("r1", "qwq", "thinking"))

        if is_current_reasoning and fast_models and current_model not in fast_models:
            selected = fast_models[0]
            final_reason = f"{reason_prefix} -> Dispatched to Fast Direct model: {selected} (No Thinking Overhead)"
        else:
            selected = current_model
            final_reason = f"{reason_prefix} -> Direct fast execution on active model: {selected}"

    # VRAM Safety Guard Check: ensure selected model fits VRAM
    if selected != current_model and raw_models:
        candidate_meta = next((m for m in raw_models if (m.get("name") or m.get("id")) == selected), None)
        if candidate_meta:
            size_bytes = candidate_meta.get("size", 0)
            arch: Dict[str, Any] = {}
            if hasattr(client, "get_model_architecture_info"):
                try:
                    arch = client.get_model_architecture_info(selected) or {}
                except Exception:
                    arch = {}
            native_ctx = None
            layers_val = None
            kv_heads_val = None
            head_dim_val = None
            sliding_window_val = None
            swa_pattern_val = None
            head_dim_swa_val = None

            if isinstance(arch, dict):
                val = arch.get("context_length")
                if isinstance(val, (int, float)) and val > 0:
                    native_ctx = int(val)
                if isinstance(arch.get("layers"), int):
                    layers_val = arch.get("layers")
                if isinstance(arch.get("kv_heads"), (int, list)):
                    kv_heads_val = arch.get("kv_heads")
                if isinstance(arch.get("head_dim"), int):
                    head_dim_val = arch.get("head_dim")
                if isinstance(arch.get("sliding_window"), int):
                    sliding_window_val = arch.get("sliding_window")
                if isinstance(arch.get("swa_pattern"), list):
                    swa_pattern_val = arch.get("swa_pattern")
                if isinstance(arch.get("head_dim_swa"), int):
                    head_dim_swa_val = arch.get("head_dim_swa")

            cfg_ctx = getattr(config, "context_window", 8192)
            eval_ctx = min(cfg_ctx, native_ctx) if native_ctx else cfg_ctx

            res = calculate_vram_breakdown(
                model_size_bytes=size_bytes,
                context_tokens=eval_ctx,
                layers=layers_val,
                kv_heads=kv_heads_val,
                head_dim=head_dim_val,
                sliding_window=sliding_window_val,
                swa_pattern=swa_pattern_val,
                head_dim_swa=head_dim_swa_val,
            )
            if not res.is_fit:
                # Revert to current model to prevent OOM
                selected = current_model
                final_reason = f"{reason_prefix} -> Candidate model exceeds VRAM, safely retained: {current_model}"

    is_swapped = (selected != current_model)

    return ModelRouteResult(
        selected_model=selected,
        task_type=task_type,
        tier=tier,
        reason=final_reason,
        is_swapped=is_swapped,
    )
