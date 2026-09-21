# locaLLM Architectural & Development Rules

Architectural standards, TUI design guidelines, menu governance, and technical specifications for **locaLLM**.

---

## 1. Core Principles
1. **Platform**: Autonomous local AI workspace powered by Ollama and OpenAI-compatible custom platforms.
2. **Deterministic Control**: Never auto-spawn background daemons silently. Control lifecycle via `Services` menu or CLI `start`/`stop`.
3. **Strict English-Only in Codebase**: All source code, docstrings, comments, UI text, menu options, CLI help, error messages, and bot responses must strictly be in English. No Indonesian or mixed-language strings anywhere in the codebase.
4. **Code Quality**: Strict Python type hints, UTF-8 console output (`sys.stdout.reconfigure(encoding='utf-8')`), and all changes verified with `python -m unittest discover -s tests -p "test_*.py"` (`self.skipTest()` when external services offline).

---

## 2. Console UI & Typography
1. **Pure Text Menu Choices**: **NO EMOJIS OR ICONS** in Questionary `choices=[]` (breaks Windows monospace alignment). Use pure text: `Assistant`, `Integrations`, `Model Manager`, `Services`, `Settings`, `Back`, `Exit`.
2. **High-Contrast Palette (No Dark Purple)**: Dim/secondary: `#aaaaaa` / `#bbbbbb`; Highlights/models/commands: `#00d7ff` (cyan); Success: `#00ff87` (green); Primary: `#ffffff` (white). Never use dim purple (`[dim]` in Rich).
3. **Minimalist Header Banner**: Unicode banner `✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ  ✦` displaying service status, endpoint, active model, model features (`Tools`, `Vision`, `Reasoning`), and GPU VRAM. No redundant title strings.
4. **Square Snake Spinner**: Custom spinner `▘▀▝▐▗▄▖▌` during model thinking or ReAct tool planning before stream tokens emit.

---

## 3. Menu Hierarchy & Navigation
```text
Main Menu:
  ├── Assistant             -> Interactive standalone chat session
  ├── Workspaces            -> Isolated environments: Switch, Create, Delete, Details, Back
  ├── Integrations          -> Channels & runners
  │     ├── Telegram        -> Telegram Bot: Start Bot, Configure Token, Whitelist Users, Back
  │     ├── WhatsApp        -> WhatsApp Bot: Start Bot, Configure Whitelist, Clear Session, Back
  │     ├── Agent & Auto    -> Autonomous Agent: Run Task, Toggle Auto-Approve Commands, Back
  │     └── Back            -> Return to Main Menu
  ├── Model Manager         -> Model management per platform
  │     ├── Ollama          -> List models, size, VRAM Fit check, Pull model, Back
  │     ├── [Custom Platform] -> OpenAI-compatible platform models, Back
  │     ├── Add Custom Platform -> Register new OpenAI-compatible platform
  │     └── Back            -> Return to Main Menu
  ├── Services              -> Server daemon lifecycle per platform
  │     ├── Ollama          -> Status, Start Server, Stop Server, Configure Endpoint, Back
  │     ├── [Custom Platform] -> Status, Set Active, Configure Endpoint/Key, Delete, Back
  │     ├── Add Custom Platform -> Register new OpenAI-compatible platform
  │     └── Back            -> Return to Main Menu
  ├── Settings              -> Global inference only: Backend, Temp, Context Window, Prompt, Reset
  └── Exit                  -> Unload VRAM and terminate application
```

### Navigation Rules:
- **Every Submenu Must Have `Back`**: Always allow returning to parent without exiting.
- **Domain Separation**: Telegram token/whitelist in `Integrations -> Telegram`; Shell auto-approve in `Integrations -> Agent & Auto`; Endpoints in `Services -> [Platform] -> Configure Endpoint`; `Settings` strictly for general inference parameters.
- **Anti-Screen-Flash-Clear**: Pause before clearing console after actions with output: `questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()`.

---

## 4. Chat & Cross-Platform Parity (CLI, Telegram, WhatsApp)
1. **Silent Tool Execution**: Tools (`list_directory`, `read_file`, `fetch_web`, `get_current_time`, `execute_command`, `get_weather`, etc.) must run silently behind loading indicators (spinner in CLI, `typing` action in bots). Never print raw JSON payloads into chat history.
2. **Context Telemetry**: Render cumulative active session token usage vs model context window (`num_ctx`, default `8,192`):
   `• Context: 2,681/8,192 tokens (32.7%) • Speed: 37.8 tok/s`
   Dynamic threshold colors: **Green** (<70%), **Yellow** (70–90%), **Red** (>=90%). Never show per-response prompt/eval tokens.
3. **Universal Slash Commands & Keywords**:
   - `/stats` (`stats`, `context`, `telemetry`): Model, tokens/limit, %, speed (`tok/s`), workspace, history depth.
   - `/model` (`model`): Active model name and features (Tools, Vision, Reasoning).
   - `/clear` / `/reset` (`reset`, `clear`, `start fresh`): Wipe session history and free memory.
   - `/help` (`help`): Command and keyword reference.
4. **Chat Ergonomics**: No redundant welcome greetings. Show concise command hint: `Commands: /help, /stats, /model, /clear, /back, /exit`. If streaming returns 0 tokens, run non-streaming fallback turn.

---

## 5. Tools & Filesystem Intelligence
1. **Smart Path Resolution (`resolve_smart_path`)**: Automatically map aliases (`downloads`, `desktop`, `documents`, `~`, `%USERPROFILE%`) to real home directories.
2. **Folder-First Listing (`list_directory`)**: Prioritize subdirectories (`[DIR]`, up to 80) above files (`[FILE]`) with summary header (`Total: X folders, Y files`).
3. **Web & GitHub (`fetch_web`)**: Direct raw `README.md` fetch for GitHub URLs.
4. **Tool Authority Mandate**: System prompts must establish direct local execution authority. Never return canned refusals like "I am only an AI".

---

## 6. Hardware & GPU Sizing Formula
1. **KV Cache (GB)**:
   - `Channels = Layers × KV_Heads × Head_Dim`
   - `Bytes_per_Token = 2 × Channels × Precision_Bytes`
   - `KV_Cache_GB = (Bytes_per_Token × Context_Tokens) / (1024³)`
   - *Precision*: 2 bytes (FP16 default) or 1 byte (FP8/Q8 quantized).
   - *GQA Awareness*: Uses `KV_Heads` (not query heads) for exact Grouped-Query Attention scaling.
   - *SWA Awareness*: Hybrid models (e.g. Gemma 4) bound local attention layers to `Window_l = 1,024` tokens.
2. **Usable VRAM (GB)**: `Usable_VRAM = Total_GPU_VRAM - OS_Display_Usage` (measured via idle `free_vram` from `pynvml` / `nvidia-smi`).
3. **Total Inference VRAM (GB)**: `Total_VRAM = Model_Weights_GB + KV_Cache_GB + CUDA_Overhead_GB` (~0.6 GB CUDA runtime & activation buffer).
4. **Validation Classification**:
   - `100% GPU (FIT)`: `Total_VRAM ≤ Usable_VRAM` (Headroom ≥ 0).
   - `SPILLOVER`: `Total_VRAM > Usable_VRAM` (partial CPU offload or RAM swap needed).
5. **Max Context Tokens**: `Max_Context = (Usable_VRAM - Model_Weights - CUDA_Overhead) × 1024³ / Bytes_per_Token` (maximum safe window without spillover).

---

## 7. Autonomous Agent & Capability-Driven Routing Architecture
1. **No Brittle Keyword Dictionaries**: Never gate tools or route models using hardcoded language-specific regex dictionaries (e.g. slang, localized phrasing, or test-case keywords). Natural language is multilingual and combinatorial.
2. **Native Tool Calling Autonomy**: The LLM itself determines when to invoke tools via function calling schemas (`tools=[]`), not external regex gatekeepers. Both Assistant and Agent modes must always expose full tools (`write_file`, `create_directory`, `read_file`, `list_directory`, `execute_command`, `fetch_web`, etc.).
3. **Capability-First Model Hierarchy**: Prioritize models declaring `"Tools"` capability and adequate parameter capacity. Never downgrade an active, capable model to a lightweight model merely because a prompt is brief or conversational.
4. **Sticky Routing (Anti-Thrashing)**: If the currently loaded model is capable and fits within VRAM headroom, retain it. Swaps only occur for explicit modality shifts (e.g. `has_image` for Vision) or dedicated specialist tasks.
5. **Unrestricted Filesystem Access**: Tools must support any valid absolute or relative path anywhere across the user's filesystem (all drives and directories), automatically scaffolding parent folders as required.
6. **Autonomous Multi-Step ReAct Loop**: The LLM autonomously determines the sequence of actions and stopping conditions. Turns loop continuously while `tool_calls` are emitted (up to `MAX_TOOL_STEPS = 25`), executing tools, updating spinners silently, and feeding observations back to the model until it outputs its final summary.
7. **Permission Policy (`always_allow`, `ask`, `deny`)**: Mutating tools (`write_file`, `create_directory`, `execute_command`) adhere to the configured policy: `always_allow` executes without prompting; `ask` interactively requests user authorization (`Allow Once`, `Always Allow (session)`, `Deny`); `deny` strictly blocks mutating operations in read-only mode.
8. **Skills & Knowledge Architecture**: Project context (`AGENTS.md`, `CLAUDE.md`) and skills (`.locallm/skills/`, `.agents/skills/`, `skills/`, and workspace knowledge) are discovered automatically from both active workspace and project root, and queryable via native tools (`list_skills`, `read_skill`).
