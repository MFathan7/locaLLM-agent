# locaLLM Development & Architectural Rules for Antigravity AI Assistant

This document defines the architectural standards, Terminal User Interface (TUI) design guidelines, menu governance, and technical specifications that must be strictly followed when developing **locaLLM**. All rules below are synthesized directly from user evaluations, reviews, and design requirements.

---

## 1. Core Principles & Philosophy
1. **Developer-First Local LLM Platform**: `locaLLM` functions as a fast, autonomous local AI workspace powered by local backends (Ollama and OpenAI-compatible custom platforms).
2. **Deterministic & Manual Server Control**: Never auto-spawn background server daemons silently. Daemon lifecycles must remain strictly under user control via the `Services` menu or the CLI `start` and `stop` commands.
3. **No Slop & High Contrast**: The console UI must be clean, responsive, aligned, and readable on Windows terminal environments (PowerShell, CMD, Windows Terminal) with dark backgrounds.
4. **Strict English-Only in Codebase**: All source code, docstrings, comments, UI text, menu options, CLI help guides, error messages, and bot responses must strictly be written in English. Do not use Indonesian or mixed-language strings anywhere in the codebase to maintain clean, professional, and consistent architecture.

---

## 2. Console UI & Typography Rules
1. **NO EMOJIS OR ICONS IN QUESTIONARY MENU CHOICES (`choices=[]`)**:
   - Emojis break monospace font column alignment on Windows terminals.
   - Menu labels **must be pure text**:
     - *Correct*: `Assistant`, `Integrations`, `Model Manager`, `Services`, `Settings`, `Back`, `Exit`.
     - *Forbidden*: `💬 Assistant`, `🤖 Integrations`, `⚙️ Settings`.
2. **Terminal Typography & High-Contrast Colors (No Dark Purple / Dim on Windows)**:
   - Avoid dark/dim purple (`[dim]` in Rich) for commands, hints, or status indicators, as it is nearly invisible on dark Windows terminals.
   - Use high-contrast light gray (`#bbbbbb` or `#aaaaaa`) for dimmed/secondary text and command hints.
   - Use `cyan` (`#00d7ff`) for model names, commands, and active highlights.
   - Use `green` (`#00ff87`) for success and normal status indicators.
   - Use `white` (`#ffffff`) for primary text and output.
3. **Minimalist & Uniform Header Banner**:
   - Always display the Unicode banner: `✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ  ✦`.
   - Display server status, endpoint, active model, detected capabilities (`Model Features: Tools, Vision, Reasoning`), and GPU VRAM capacity.
   - Do not add redundant title strings like *"Local LLM Platform"* inside the banner.
4. **Square Snake Loading Spinner**:
   - Use the custom **Square Snake Spinner** (`▘▀▝▐▗▄▖▌`) whenever the model is thinking or processing ReAct agent tool steps before the first stream token is emitted.

---

## 3. Menu Architecture & TUI Navigation
Any menu additions or refactorings must strictly follow this hierarchical structure:

```text
Main Menu:
  ├── Assistant             -> Interactive standalone chat session
  ├── Workspaces            -> Isolated environments: Switch, Create, Delete, Details, Back
  ├── Integrations          -> Channels & runner integrations
  │     ├── Telegram        -> Telegram Bot runner: Start Bot, Configure Token, Whitelist Users, Back
  │     ├── WhatsApp        -> WhatsApp Bot runner: Start Bot, Configure Whitelist, Clear Session, Back
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
  ├── Settings              -> Global inference parameters only (Backend, Temp, Context Window, Prompt, Reset)
  └── Exit                  -> Terminate application
```

### Submenu Navigation Rules:
1. **Every Submenu Must Have a `Back` Option**: Users must always be able to return to the parent menu without exiting the application.
2. **Platform & Domain Separation**:
   - Telegram bot tokens and user ID whitelists belong in `Integrations -> Telegram`, NOT in `Settings`.
   - Shell auto-approve command toggles belong in `Integrations -> Agent & Auto`, NOT in `Settings`.
   - Host endpoints belong in `Services -> [Platform] -> Configure Endpoint`.
   - The `Settings` menu is strictly reserved for general model inference settings (`Active Backend`, `Sampling Temperature`, `Context Window Limit`, `System Prompt`).
3. **Prevent Screen Flash Clear**:
   - After executing an action that outputs text (e.g., bot tests, agent task runs, or service status checks), **always pause before returning**:
     ```python
     questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
     ```
   - Do not let the menu loop invoke `console.clear()` before the user has read the execution output.

---

## 4. Interactive Assistant & Chat Session Standards
1. **Silent Tool Execution**:
   - In interactive assistant sessions (`locaLLM chat`), tool invocations (`list_directory`, `read_file`, `fetch_web`, `get_current_time`, etc.) **must execute silently behind the thinking spinner**.
   - Do not print verbose raw execution logs such as `• Executing Tool:...` or `• Tool Result:...` in the chat window, keeping chat history clean and concise.
2. **Accurate Context Usage Telemetry (Active Session vs Limit)**:
   - Render a real-time telemetry line beneath every AI response showing the cumulative token context used in the active session compared to the model's context window limit (`num_ctx`, default `8,192` tokens):
     ```text
     • Context: 2,681/8,192 tokens (32.7%) • Speed: 37.8 tok/s
     ```
   - Never display per-response tokens (`Prompt: ... | Response: ...`). Always display the cumulative active conversation usage.
   - Dynamic threshold colors: **Green** (<70%), **Yellow** (70–90%), **Red** (>=90%).
3. **No Redundant Welcome Greeting**:
   - Do not print lines like `Interactive Assistant session started. Using model: ...` or capabilities lists inside the chat prompt, as this is already visible in the Header Banner.
   - Only display a brief, high-contrast light gray command hint:
     ```text
     Commands: /help, /stats, /model, /clear, /back, /exit
     ```
4. **Double Fallback for Silent Responses**:
   - If token streaming returns 0 tokens, the system **must automatically execute a non-streaming fallback turn** or display an informative notice. The AI must never silently stop after thinking without delivering an answer.

---

## 5. Tools & Filesystem Intelligence Standards
1. **Smart Path Resolution (`resolve_smart_path`)**:
   - Any tool accepting file or directory paths (`list_directory`, `read_file`, agent execution tools) must use smart path resolution.
   - OS directory aliases must automatically map to the user's real home directories:
     - `downloads` / `download` -> `Path.home() / "Downloads"`
     - `desktop` -> `Path.home() / "Desktop"`
     - `documents` -> `Path.home() / "Documents"`
     - `~` or `%USERPROFILE%` -> `Path.home()`
2. **Folder-First Directory Listing**:
   - `list_directory` must prioritize all subdirectories (`[DIR]`) at the very top (up to 80 folders) before listing files (`[FILE]`).
   - Include a summary header (`Total: X folders, Y files`) so target folders are never buried or truncated by long file lists.
3. **Web & GitHub Fetching (`fetch_web`)**:
   - Provide `fetch_web` for webpage inspections. If the link is a GitHub repository, fetch the raw `README.md` directly so the model can summarize the project instantly without requiring shell commands.
4. **Tool Authority Mandate & RLHF Refusal Prevention**:
   - System prompts must explicitly instruct the model that it possesses direct local tool execution authority and **is strictly forbidden from rejecting local file/directory requests with canned refusals like "I am only an AI"**.
   - The system prompt architecture must remain modular and composable, allowing future **Skills**, **Knowledge (RAG)**, or **Custom Agent Rules** to be appended without breaking core tool authority.

---

## 6. Hardware & GPU Sizing Formula
1. **VRAM Sizing Formula**:
   $$\text{Required VRAM} = \text{Model Size (GB)} + 2.0\text{ GB (KV Cache \& Runtime Buffer)}$$
2. **Compatibility Status**:
   - Display `[bold green]FIT[/]` if $\text{Model Size} + 2.0 \le \text{Free VRAM}$.
   - Display `[bold red]OFFLOAD (CPU/RAM)[/]` if it exceeds free GPU VRAM.

---

## 7. Code Quality & Testing Policy
1. **Strict Type Safety & Windows Encoding**:
   - Always include standard Python type hints on new and modified functions.
   - Ensure the console is configured for UTF-8: `sys.stdout.reconfigure(encoding='utf-8')`.
2. **Mandatory Test Verification**:
   - All code changes must be verified against the test suite:
     ```powershell
     python -m unittest discover -s tests -p "test_*.py"
     ```
   - Integration tests requiring external running daemons must use `self.skipTest()` when the service is offline so that the suite remains green across all environments.

---

## 8. Strict English-Only in Codebase
1. **Strict English Requirement**:
   - All source code, docstrings, comments, variable names, UI text, Questionary menu choices, CLI help guides, error messages, test fixtures, and bot responses must strictly be written in English.
   - Never use Indonesian or mixed-language strings in any script or user-facing interface.

---

## 9. Cross-Platform Uniformity & Context Telemetry Standard
1. **Symmetrical Multi-Platform Experience (CLI, Telegram, WhatsApp)**:
   - All supported platforms (`Interactive CLI Assistant`, `Telegram Bot`, and `WhatsApp Bot`) must maintain strict feature, visual, and telemetry parity.
   - **Real-Time Context Usage Telemetry**:
     - Every inference turn across all channels must calculate and expose cumulative active session tokens against the model's context limit (`num_ctx`, default `8,192` tokens):
       ```text
       • Context: 2,681/8,192 tokens (32.7%) • Speed: 37.8 tok/s
       ```
     - Dynamic threshold styling: **Green** (<70%), **Yellow** (70–90%), **Red** (>=90%).
   - **Universal Slash Commands & Natural Keywords**:
     - All bot platforms must support identical essential operational commands:
       - `/stats` (or natural keywords `stats`, `context`, `telemetry`): Returns active model, cumulative token usage against limit, percentage, tokens/sec speed, active workspace, and session history depth.
       - `/model` (or `model`): Displays current model name and detected features (Tools, Vision, Reasoning).
       - `/clear` / `/reset` (or `reset`, `clear`, `start fresh`): Wipes session history and frees memory cleanly.
       - `/help` (or `help`): Displays command reference and keyword guide.
   - **Silent Tool Execution**:
     - In all interactive channels, function and tool execution must proceed silently behind native loading feedback (custom square snake spinner in CLI, `typing` chat action in Telegram and WhatsApp) without polluting the chat history with raw JSON execution payloads.



