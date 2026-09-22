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
    r"\b(write_file|create_directory|read_file|list_directory|search_web)\b",
    # Terminal, system commands, web/API fetching, and database
    r"\b(run|execute|jalankan)\s+(?:command|cmd|terminal|powershell|bash|shell|script)\b",
    r"\b(curl|wget|fetch|download|unduh|ping|search|googling|cari\s+web|search_web|http[s]?://)\b",
    r"\b(berita|news|terkini|terbaru|hari ini|today|latest|current events|headline|isu terkini)\b",
    r"\b(kabar\s+berita|update\s+berita|info\s+terkini|kabar\s+terbaru)\b",
    r"\b(presiden|menteri|pemerintahan|politik|pilkada|pemilu)\b.*?\b(terkini|terbaru|saat ini|sekarang|kali ini)\b",
    r"\b(weather|temperature|forecast|suhu|cuaca|sqlite_query|sqlite_schema)\b",
    r"\b(query|cek|inspeksi|isi|select|update|delete|insert)\b.*?\b(database|tabel|sqlite|db)\b",
    r"\b(tool call|function calling|schema json|json schema|trigger_\w+|execute tool)\b",
]

# Fast / Direct factual signals
FAST_PATTERNS = [
    r"^(hi|hello|halo|hey|p|tes|test|ping|good morning|good afternoon|good evening|selamat pagi|siang|sore|malam)[.!?]*$",
    r"\b(what is|who is|artinya|terjemahkan|translate|bullet points?|summarize|ringkas|rangkum|singkatkan)\b",
    r"\b(in simple terms|secara sederhana|analogi|explain simply)\b",
]


def is_match_negated(text: str, match_start: int) -> bool:
    """Check if a matched action phrase is preceded by an immediate negation within the same clause.

    Prevents false positives on prompts like:
    - 'jangan bikin file ya' -> negated
    - 'nggak usah coding ya' -> negated
    - 'without creating any files' -> negated
    - 'don't run scripts' -> negated

    Correctly handles double-negative / positive idioms:
    - 'jangan lupa bikin file' -> NOT negated (positive intent)
    - 'not without creating' -> NOT negated (positive intent)
    """
    prefix = text[max(0, match_start - 40):match_start]
    clause_delimiters = [",", ".", ";", "!", "?", "\n", ":"]
    last_boundary = -1
    for delim in clause_delimiters:
        idx = prefix.rfind(delim)
        if idx > last_boundary:
            last_boundary = idx
    if last_boundary != -1:
        prefix = prefix[last_boundary + 1:]

    prefix_clean = prefix.strip().lower()
    if not prefix_clean:
        return False

    if re.search(r"\b(jangan\s+lupa|don'?t\s+forget|never\s+forget|tidak\s+lupa)\b", prefix_clean, re.IGNORECASE):
        return False

    NEGATION_WORDS = r"\b(jangan|nggak\s+usah|gak\s+usah|tidak\s+usah|tidak\s+perlu|nggak\s+perlu|gak\s+perlu|tanpa|bukan|dilarang|don'?t|do\s+not|never|without|stop|avoid|no\s+need\s+to)\b"
    return bool(re.search(NEGATION_WORDS, prefix_clean, re.IGNORECASE))


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

    # 1. Tool intent check with negation guard (filesystem paths, file creation, command, web, weather)
    for pat in TOOL_PATTERNS:
        for match in re.finditer(pat, clean, re.IGNORECASE):
            # Structural patterns (absolute paths like C:\ or POSIX paths) cannot be negated
            is_structural = (
                bool(re.match(r"[a-zA-Z]:[/\\]", match.group(0)))
                or match.group(0).startswith(("/", "./", "../", "~"))
            )
            if is_structural or not is_match_negated(clean, match.start()):
                return TaskType.TOOLS, TaskTier.DEEP_REASONING, "System tool / schema extraction intent"

    # 2. Coding check with negation guard
    coding_score = 0
    for pat in CODING_PATTERNS:
        for match in re.finditer(pat, clean, re.IGNORECASE):
            # Markdown code fences and inline ticks are structural and un-negatable
            is_structural = match.group(0).startswith(("```", "`"))
            if is_structural or not is_match_negated(clean, match.start()):
                coding_score += 2
                break

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
            size = m.get("size", 0)
            if not size:
                # Estimate size in bytes from parameter tag in name (e.g. 14b -> 14GB, 7b -> 7GB)
                match = re.search(r"(\d+(?:\.\d+)?)[bB]\b", name)
                if match:
                    size = int(float(match.group(1)) * 1024**3)
            model_size_map[name] = size

    # Determine baseline fallback model: prioritize generalist / tool-capable models over pure coder models
    general_models = [
        m for m in model_names
        if not any(k in m.lower() for k in ("coder", "code", "dev", "starcoder"))
    ]
    preferred_fallback = (
        general_models[0]
        if general_models
        else (model_names[0] if model_names else "gemma4:12b")
    )

    fallback_model = (
        config.ollama_model
        if config.ollama_model and config.ollama_model.lower() != "auto"
        else preferred_fallback
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

    def _pick_first_fitting(candidates: List[str]) -> Optional[str]:
        """Return the highest-ranked candidate that fits inside available VRAM."""
        for cand in candidates:
            if check_model_vram_fit(cand, raw_models, client, config):
                return cand
        return None

    selected = current_model
    final_reason = ""

    # Selection Strategy with Sticky Routing (Anti-Swap) and VRAM Fit
    if task_type == TaskType.VISION:
        if current_model in vision_models:
            selected = current_model
            final_reason = f"{reason_prefix} -> Retained active Vision model: {selected}"
        elif vision_models:
            fit_cand = _pick_first_fitting(vision_models)
            if fit_cand:
                selected = fit_cand
                final_reason = f"{reason_prefix} -> Dispatched to Vision model: {selected}"
            else:
                selected = current_model
                final_reason = f"{reason_prefix} -> Candidate model exceeds VRAM, safely retained: {current_model}"
        else:
            selected = current_model
            final_reason = f"{reason_prefix} -> No dedicated Vision model, retained: {selected}"

    elif task_type == TaskType.REASONING:
        if reasoning_models and current_model not in reasoning_models:
            fit_cand = _pick_first_fitting(reasoning_models)
            if fit_cand:
                selected = fit_cand
                final_reason = f"{reason_prefix} -> Dispatched to Reasoning specialist: {selected} (Deep Thinking)"
            else:
                selected = current_model
                final_reason = f"{reason_prefix} -> Candidate model exceeds VRAM, safely retained: {current_model}"
        elif reasoning_models and any(k in reasoning_models[0].lower() for k in ("r1", "qwq", "qwen")) and not any(k in current_model.lower() for k in ("r1", "qwq", "qwen")):
            fit_cand = _pick_first_fitting(reasoning_models)
            if fit_cand:
                selected = fit_cand
                final_reason = f"{reason_prefix} -> Dispatched to Primary Reasoning specialist: {selected}"
            else:
                selected = current_model
                final_reason = f"{reason_prefix} -> Candidate model exceeds VRAM, safely retained: {current_model}"
        else:
            selected = current_model
            final_reason = f"{reason_prefix} -> Retained active engine: {selected} (Deep Thinking)"

    elif task_type == TaskType.CODING:
        if current_model in coder_models:
            selected = current_model
            final_reason = f"{reason_prefix} -> Retained active Coder: {selected}"
        elif coder_models:
            fit_cand = _pick_first_fitting(coder_models)
            if fit_cand:
                selected = fit_cand
                final_reason = f"{reason_prefix} -> Dispatched to Coding specialist: {selected}"
            else:
                selected = current_model
                final_reason = f"{reason_prefix} -> Candidate model exceeds VRAM, safely retained: {current_model}"
        else:
            selected = current_model
            final_reason = f"{reason_prefix} -> Generalist handling code: {selected}"

    elif task_type == TaskType.TOOLS:
        coder_tool_models = [m for m in coder_models if m in tool_models]
        coder_tool_models.sort(key=lambda m: -model_size_map.get(m, 0))

        clean_lower = prompt.lower()
        is_coding_context = (
            "code" in reason_prefix.lower()
            or "architecture" in reason_prefix.lower()
            or any(k in clean_lower for k in ("code", "script", "project", "app", "file", "program", "def ", "class "))
        )

        if is_coding_context and coder_tool_models:
            if current_model in coder_tool_models:
                selected = current_model
                final_reason = f"{reason_prefix} -> Retained active Coding Tool specialist: {selected}"
            else:
                fit_cand = _pick_first_fitting(coder_tool_models)
                if fit_cand:
                    selected = fit_cand
                    final_reason = f"{reason_prefix} -> Dispatched to Specialist Coding Agent: {selected}"
                else:
                    selected = current_model
                    final_reason = f"{reason_prefix} -> Candidate model exceeds VRAM, safely retained: {current_model}"
        else:
            should_elevate = (
                tool_models
                and tool_models[0] != current_model
                and (current_model in fast_models or model_size_map.get(tool_models[0], 0) > model_size_map.get(current_model, 0))
            )
            if should_elevate:
                fit_cand = _pick_first_fitting(tool_models)
                if fit_cand:
                    selected = fit_cand
                    final_reason = f"{reason_prefix} -> Dispatched to Primary Tool specialist: {selected}"
                else:
                    selected = current_model
                    final_reason = f"{reason_prefix} -> Candidate model exceeds VRAM, safely retained: {current_model}"
            elif current_model in tool_models:
                selected = current_model
                final_reason = f"{reason_prefix} -> Retained Tool-capable model: {selected}"
            elif tool_models:
                fit_cand = _pick_first_fitting(tool_models)
                if fit_cand:
                    selected = fit_cand
                    final_reason = f"{reason_prefix} -> Dispatched to Tool specialist: {selected}"
                else:
                    selected = current_model
                    final_reason = f"{reason_prefix} -> Candidate model exceeds VRAM, safely retained: {current_model}"
            else:
                selected = current_model
                final_reason = f"{reason_prefix} -> Retained active model for tools: {selected}"

    else:  # FAST_CHAT
        current_features: List[str] = []
        if hasattr(client, "get_model_features"):
            try:
                current_features = client.get_model_features(current_model)
            except Exception:
                current_features = []
        is_current_reasoning = "Reasoning" in current_features or any(k in current_model.lower() for k in ("r1", "qwq", "thinking"))
        is_current_coder = current_model in coder_models

        # If current model is a pure reasoning model or a pure coder model, swap to a fast generalist model
        non_coder_fast = [m for m in fast_models if m not in coder_models]
        if (is_current_reasoning or is_current_coder) and non_coder_fast:
            fit_cand = _pick_first_fitting(non_coder_fast)
            if fit_cand and fit_cand != current_model:
                selected = fit_cand
                final_reason = f"{reason_prefix} -> Dispatched to Fast Generalist model: {selected}"
            else:
                selected = current_model
                final_reason = f"{reason_prefix} -> Direct fast execution on active model: {selected}"
        elif is_current_reasoning and fast_models and current_model not in fast_models:
            fit_cand = _pick_first_fitting(fast_models)
            if fit_cand:
                selected = fit_cand
                final_reason = f"{reason_prefix} -> Dispatched to Fast Direct model: {selected} (No Thinking Overhead)"
            else:
                selected = current_model
                final_reason = f"{reason_prefix} -> Direct fast execution on active model: {selected}"
        else:
            selected = current_model
            final_reason = f"{reason_prefix} -> Direct fast execution on active model: {selected}"

    is_swapped = (selected != current_model)

    return ModelRouteResult(
        selected_model=selected,
        task_type=task_type,
        tier=tier,
        reason=final_reason,
        is_swapped=is_swapped,
    )


def check_model_vram_fit(
    model_name: str,
    raw_models: List[Dict[str, Any]],
    client: Any,
    config: LocaLLMConfig,
) -> bool:
    """Check if the candidate model fits in GPU VRAM without spillover."""
    candidate_meta = next((m for m in raw_models if (m.get("name") or m.get("id")) == model_name), None)
    if not candidate_meta:
        return True

    size_bytes = candidate_meta.get("size", 0)
    if not size_bytes:
        match = re.search(r"(\d+(?:\.\d+)?)[bB]\b", model_name)
        if match:
            size_bytes = int(float(match.group(1)) * 1024**3)

    arch: Dict[str, Any] = {}
    if hasattr(client, "get_model_architecture_info"):
        try:
            arch = client.get_model_architecture_info(model_name) or {}
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
    return res.is_fit
