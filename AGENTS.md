# locaLLM Architectural & Development Rules

Architectural standards, TUI design guidelines, and technical specifications for **locaLLM**.

---

## 1. Core Principles
1. **Platform**: Autonomous local AI platform powered by Ollama and OpenAI-compatible inference backends.
2. **Deterministic Control**: Never auto-spawn background daemons silently. Control lifecycle via `Services` menu or CLI `start`/`stop`.
3. **Strict English-Only in Codebase**: All source code, docstrings, comments, UI text, menu options, CLI help, error messages, and bot responses must strictly be in English. No Indonesian or mixed-language strings in the codebase.
4. **Code Quality**: Strict Python type hints, UTF-8 console output (`sys.stdout.reconfigure(encoding='utf-8')`), and all changes verified with `python -m unittest discover -s tests -p "test_*.py"` (`self.skipTest()` when external services offline).

---

## 2. Console UI & Typography
1. **Pure Text Choices (NO Emojis/Icons)**: In Questionary `choices=[]`, use pure text only (`Assistant`, `Integrations`, `Model Manager`, `Services`, `Settings`, `Back`, `Exit`). Never use emojis/icons (breaks Windows monospace alignment).
2. **High-Contrast Palette**: Dim/secondary: `#aaaaaa` / `#bbbbbb`; Highlights/models: `#00d7ff` (cyan); Success: `#00ff87` (green); Primary: `#ffffff` (white). Never use dim purple (`[dim]` in Rich).
3. **Header Telemetry Banner**: Unicode banner `✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ  ✦` displaying service status, endpoint, active model, features, GPU VRAM bar, headroom, compute/temp, host RAM/CPU, and resident models.
4. **Navigation & Flow**: Every submenu must have `Back`. Pause before clearing console after output actions: `questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()`.

---

## 3. Chat & Streaming Engine
1. **Silent Tool Execution**: Tools run quietly behind spinners (`▘▀▝▐▗▄▖▌`) or bot typing actions. Never dump raw JSON payloads into chat history.
2. **Live Typing Effect**: Assistant tokens stream with typewriter cursor (`▌`), smooth cadence, and auto-closing markdown fences during generation to preserve syntax highlighting.
3. **Context Telemetry**: Show cumulative session usage: `• Context: X/Y tokens (Z%) • Speed: N tok/s` (Green <70%, Yellow 70–90%, Red >=90%). Never print per-turn prompt/eval breakdown.
4. **Slash Commands**: Support `/top` (Live Monitor), `/stats`, `/model`, `/clear`, `/sessions`, `/help`, `/back`, `/exit`. Fallback to non-streaming turn if stream yields 0 tokens.

---

## 4. Tools & Filesystem Intelligence
1. **Modular Tool Registry (`locallm/core/tools/`)**: Register tools via `@tool(...)` with explicit JSON schema and `is_mutating: bool`. Never hardcode ad-hoc dictionary lists or manual dispatch switches.
2. **Permission Policy**: Mutating tools (`is_mutating=True`) adhere strictly to configured policy: `always_allow`, `ask` (interactive approval), or `deny` (read-only mode).
3. **Pagination & Boundaries**: Content-returning tools must support `offset: int = 0` and `max_chars: int = 4000` chunking. File paths resolve via `resolve_smart_path(...)` with alias expansion (`~`, `downloads`, etc.) and boundary isolation.
4. **UI Synchronization (`locallm/core/tools/ui.py`)**: Every tool must have `describe_tool_action` (spinner text) and `format_live_tool_report` (completion line).
5. **Direct Execution Authority**: Models must never refuse with "I am only an AI"; use proactive search and local execution tools directly.

---

## 5. Hardware & VRAM Sizing Formula
1. **KV Cache Calculation**:
   - `Channels = Layers × KV_Heads × Head_Dim` (uses GQA `KV_Heads`; binds SWA hybrid models to `Window_l = 1024`).
   - `Bytes_per_Token = 2 × Channels × Precision_Bytes` (FP16: 2B, FP8/Q8: 1B).
   - `KV_Cache_GB = (Context_Tokens × Bytes_per_Token) / (1024³)`.
2. **Validation**: `Total_VRAM = Model_Weights_GB + KV_Cache_GB + CUDA_Overhead (~0.6 GB)`.
   - `100% GPU (FIT)`: `Total_VRAM ≤ Usable_VRAM` (`Usable_VRAM = Total_VRAM - OS_Display_Usage`).
   - `SPILLOVER`: `Total_VRAM > Usable_VRAM` (warns about CPU offload/RAM swap).

---

## 6. Autonomous Agent & Routing Architecture
1. **No Brittle Keyword Regexes**: Never gate tools or route models via hardcoded localized regexes. LLM determines tool calling autonomously via function schemas (`tools=[]`).
2. **Sticky Capability-First Routing**: Prioritize models declaring `Tools` and adequate parameter capacity (`14B` > `7B` > `3B`). Retain the active model if it fits VRAM headroom (anti-thrashing).
3. **Multi-Step ReAct Loop**: Autonomous turns loop continuously while `tool_calls` are emitted (up to `MAX_TOOL_STEPS = 25`).
4. **Zero-Hardcoding Plugin System**: Discover extensions dynamically via `plugin.json` manifests (Local `<cwd>/plugins/` > Workspace > Global `~/.locallm/plugins/`).
