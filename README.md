# locaLLM

A developer-first CLI and interactive Terminal User Interface (TUI) platform built in Python and natively integrated with **Ollama** and **OpenAI-compatible Custom Platforms** (e.g. vLLM, LocalAI, text-generation-webui). `locaLLM` transforms your local LLMs into turn-key capabilities: **Interactive AI Assistant**, **Telegram Bot**, **WhatsApp Bot**, **Autonomous ReAct Agent**, **Isolated Workspaces**, and **Hardware-Aware Model Manager**.

---

## Key Features

- **Clean Terminal User Interface (TUI)**: Keyboard-driven menu navigation (`Up`/`Down`/`Enter`) with a dedicated `Back` option in every submenu and pure text labels designed to maintain strict monospace alignment on Windows terminals without emoji distortion.
- **Cross-Platform Parity & Context Telemetry**:
  - Standardized context usage & speed telemetry across Interactive Assistant, Telegram Bot, and WhatsApp Bot:
    ```text
    • Context: 2,681/8,192 tokens (32.7%) • Speed: 37.8 tok/s
    ```
  - Calculates cumulative active session tokens against the model's context limit (`num_ctx`, default `8,192` tokens).
  - Dynamic threshold coloring: **Green** (<70%), **Yellow** (70–90%), **Red** (>=90%).
  - Universal slash commands and natural keyword parity across all channels: `/stats` (or `stats`, `context`, `telemetry`), `/model` (or `model`), `/clear`/`/reset` (or `reset`, `clear`, `start fresh`), and `/help` (or `help`).
- **Model Manager & Hardware Sizing (VRAM Checker)**:
  - Automatic GPU detection (NVIDIA VRAM) and system memory inspection.
  - VRAM sizing formula: $\text{Required VRAM} = \text{Model Size (GB)} + 2.0\text{ GB (KV Cache \& Runtime Buffer)}$ to determine whether a model fits in GPU VRAM (`FIT`) or requires CPU/RAM offloading (`OFFLOAD`).
  - Pull new models from the Ollama registry with real-time console download progress.
  - Multi-platform support: Seamlessly register, inspect, and switch between Ollama and OpenAI-compatible custom backends.
- **Service Lifecycle Manager (`locaLLM start / stop`)**:
  - Full manual control to start and stop background Ollama server processes or monitor custom platforms without silent auto-spawning.
- **Interactive Assistant (`locaLLM chat`)**:
  - Streaming Markdown responses in real time with syntax-highlighted code blocks.
  - **Silent Native Tool Automation**: The model autonomously executes local tools—checking time (`get_current_time`), working directory inspection (`get_current_directory`), smart folder listing (`list_directory` supporting aliases like `downloads`, `desktop`, `documents`), file inspection (`read_file`), web and GitHub analysis (`fetch_web`), shell command execution (`execute_command`), and weather checks (`get_weather`)—silently behind a rotating thinking spinner without cluttering the chat history.
  - **Double Fallback Mechanism**: If token streaming returns 0 tokens, the system automatically executes a non-streaming fallback turn so the model never silently exits.
- **Integrations & Bot Runners**:
  - **Telegram (`locaLLM telegram`)**: Run your local model as a 24/7 Telegram bot featuring multi-user memory, allowed user ID whitelist, native Telegram tools (photo sending, document delivery, animated dice), and automatic markdown-to-HTML formatting.
  - **WhatsApp (`locaLLM whatsapp`)**: Run your local model as a WhatsApp bot featuring terminal QR code pairing, multi-turn memory, allowed phone number whitelisting, automatic 15-digit LID-to-phone number resolution, group chat support with quoted replies, and silent tool execution.
  - **Autonomous Agent (`locaLLM agent`)**: A ReAct autonomous agent capable of executing multi-step shell commands, reading files, writing files, and inspecting URLs, with optional command auto-approval toggle.
- **Conversational CLI Guide & Persona Farewell**:
  - `locaLLM --help` delivers an interactive, styled assistant guide with banner, categorized command groups, and real-world usage examples.
  - Gracefully unloads model weights (`keep_alive: 0`) and outputs a clean farewell confirmation upon exit.
- **Square Snake Loading Animation**:
  - A minimalist rotating square snake spinner (`▘▀▝▐▗▄▖▌`) that runs while the model is thinking or reasoning before streaming tokens, as well as during agent tool planning.
- **Isolated Workspaces & Custom Skills/Knowledge (Zero-Leakage Guarantee)**:
  - Isolate knowledge bases, agent skills, and system directives per project (`~/.locallm/workspaces/<name>/`).
  - **Strict Zero-Bleed**: When a workspace is active, only its own knowledge and skills are loaded into the model context. No cross-contamination from the default workspace or other projects.
  - **Drop-in Skills & Knowledge**: Easily drop any `.md` or `.txt` reference documents, engineering guidelines, or domain playbooks directly into `skills/` or `knowledge/`.
  - **GitHub Skill Installer**: Install agent skills directly from GitHub repositories using pure Python with automatic filtering of clutter (`.git`, `tests/`, images, binary files).
- **Single-Prompt Execution (`locaLLM run "<prompt>"`)**:
  - Execute a single prompt directly from the terminal for scripting and piping workflows, complete with native tool calling support and active workspace awareness.

---

## TUI Menu Structure

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

---

## Installation & Requirements

### Prerequisites:
- Python 3.9+
- Ollama service running (default: `http://127.0.0.1:11434`) or any OpenAI-compatible server (e.g. vLLM, LocalAI, etc.)
- Node.js 18+ (required only if running the WhatsApp bot integration via Baileys)
- NVIDIA GPU (optional, for accelerated VRAM inference)

### Install Python Dependencies:
```powershell
pip install -r requirements.txt
```

### Register CLI Command (Optional):
To run `locaLLM` directly from any command line prompt:
```powershell
pip install -e .
```
Or use the bundled batch launcher script:
```powershell
.\locaLLM.bat <parameters>
```

---

## CLI Usage Guide

### 1. Launch Interactive TUI (Main Menu)
Run with no arguments:
```powershell
locaLLM
# or
python -m locallm
```

### 2. Launch Interactive Assistant Directly
```powershell
locaLLM chat
```
You can also specify a model and workspace on launch:
```powershell
locaLLM chat --model gemma4:12b -w my-project
```

### 3. Run the Telegram Bot
```powershell
locaLLM telegram
```
*Note: If no bot token is found, locaLLM will prompt for your token from `@BotFather` and save it to `~/.locallm/config.json` automatically.*

### 4. Run the WhatsApp Bot
```powershell
locaLLM whatsapp
```
*Note: On first run, a QR code will render directly in your terminal. Scan it with WhatsApp (Linked Devices) to pair.*

### 5. Run the Autonomous Agent
Interactive mode:
```powershell
locaLLM agent
```
Direct one-shot task execution:
```powershell
locaLLM agent --task "Read README.md and create a concise summary in summary.txt"
```

### 6. Single-Shot Prompt Execution (Scripting & Automation)
```powershell
locaLLM run "Write a Python function to compute Fibonacci numbers with memoization"
```

### 7. Inspect Installed Models & VRAM Compatibility
```powershell
locaLLM models
```

### 8. Service Lifecycle & Custom Platform Control
Start or stop inference backend daemons, or manage custom OpenAI-compatible platforms:
```powershell
# Start Ollama in the background
locaLLM start ollama

# Stop running Ollama processes
locaLLM stop ollama

# Check status of all configured services and platforms
locaLLM service status

# Register and switch custom OpenAI-compatible platforms
locaLLM platform list
locaLLM platform add vllm --endpoint http://127.0.0.1:8000/v1
locaLLM platform use vllm
locaLLM platform remove vllm
```

### 9. Inspect Hardware & Connection Status
```powershell
locaLLM status
```

### 10. Manage Isolated Workspaces (CLI)
```powershell
# List all installed workspaces and active status
locaLLM workspace list

# Switch active workspace globally
locaLLM workspace use my-project

# Create a new isolated workspace
locaLLM workspace create security-audit -d "Penetration testing & code review"

# Configure custom system instructions (stored in workspace.json)
locaLLM workspace instruct "Focus on OWASP Top 10 and secure code review"

# Add a knowledge document (via free text or file)
locaLLM workspace add-knowledge api-spec --content "# API Specification`n..."
locaLLM workspace add-knowledge runbook --file ./docs/runbook.md

# Add a manual skill file (saved as markdown in skills/)
locaLLM workspace add-skill code-review --content "# Code Review Rules`n..."

# Install skills directly from GitHub (pure Python, zero npm/git binaries needed)
locaLLM workspace install organization/agent-skills --skill coding-standards
locaLLM workspace install https://github.com/organization/agent-skills/tree/main/skills/audit-tool

# Delete an inactive custom workspace (default cannot be deleted)
locaLLM workspace delete security-audit

# Override active workspace on the fly for any execution
locaLLM chat -w my-project
locaLLM agent -w security-audit
```

---

## Cross-Platform Command Parity

All supported platforms (**Interactive Assistant CLI**, **Telegram Bot**, and **WhatsApp Bot**) share identical commands and natural language triggers:

| Command | Natural Keywords | Description |
| :--- | :--- | :--- |
| `/stats` | `stats`, `context`, `telemetry` | Displays active model, cumulative token usage against limit, percentage, speed (`tok/s`), and history depth. |
| `/model` | `model` | Displays the currently active model and detected capabilities (Tools, Vision, Reasoning). |
| `/clear` | `/reset`, `clear`, `reset`, `start fresh` | Wipes conversation history for the active session and frees memory cleanly. |
| `/help` | `help` | Displays command reference and keyword guide. |
| `/new` | `new session` | Starts a fresh session while archiving previous conversation turns (CLI / Telegram). |

---

## Workspaces, Knowledge & Custom Skills

`locaLLM` features a developer-first **Workspace System** designed for high customization, rapid skill installation, and absolute isolation. Each workspace acts as an independent sandbox containing project-specific knowledge, custom agent skills, and system instructions.

### Strict Zero-Bleed Isolation
Unlike platforms where default knowledge leaks or clashes across environments, `locaLLM` enforces **100% strict isolation**:
- When Workspace `A` is active, the model exclusively accesses knowledge, skills, and instructions located in Workspace `A`.
- Nothing from `default` or other workspaces leaks into the prompt context.

### Workspace Folder Anatomy
All workspaces are stored at `~/.locallm/workspaces/<workspace_name>/`:

```text
~/.locallm/workspaces/<workspace_name>/
├── workspace.json          # Metadata, description, and workspace-specific system directives
├── knowledge/              # Reference files, SOPs, documentation, API specs (.md, .txt)
├── skills/                 # Agent skills, playbooks, guidelines (.md, .txt)
└── sessions/               # Isolated storage for multi-turn session persistence
```

### Pure Python Skill Installer & Bloat Filtering
`locaLLM` includes an integrated skill installer implemented in pure Python with zero external binary dependencies:
- **Multi-Skill Repositories**: When pointing to repositories with multiple skills, `locaLLM` inspects the archive in-memory and allows you to select only the specific skill(s) you need (via interactive checklist in the TUI or `--skill <name>` in the CLI).
- **Subpath Support**: Direct links to subpaths (e.g. `github.com/org/repo/tree/main/skills/my-skill`) install only the specified subfolder.
- **Strict Bloat Filtering**: Non-documentation clutter (`.git`, `.github`, `tests/`, build artifacts, images, binary files) is filtered out, preserving local context window budget.

---

## Configuration

Configuration settings are stored automatically at:
`~/.locallm/config.json` (Windows: `C:\Users\<username>\.locallm\config.json`).

Example configuration:
```json
{
  "active_backend": "ollama",
  "ollama_host": "http://127.0.0.1:11434",
  "custom_platforms": [
    {
      "name": "vllm",
      "api_base": "http://127.0.0.1:8000/v1",
      "api_key": "",
      "default_model": "meta-llama/Llama-3-8B-Instruct"
    }
  ],
  "default_model": "gemma4:12b",
  "temperature": 0.7,
  "context_window": 8192,
  "system_prompt": "You are locaLLM, a helpful, fast, and intelligent local AI assistant.",
  "active_workspace": "default",
  "telegram_token": "YOUR_TELEGRAM_BOT_TOKEN",
  "telegram_allowed_users": [],
  "whatsapp_enabled": false,
  "whatsapp_allowed_numbers": ["628123456789"],
  "whatsapp_session_dir": "",
  "agent_auto_approve_commands": false
}
```

All settings can be configured interactively through the `Settings`, `Workspaces`, `Integrations`, and `Services` menus in the TUI, or via the `locaLLM config` CLI command.
