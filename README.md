# locaLLM

```text
       █░░ █▀█ █▀▀ ▄▀█ █░░ █░░ █▀▄▀█
       █▄▄ █▄█ █▄▄ █▀█ █▄▄ █▄▄ █░▀░█
              ✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ  ✦
```

> **Developer-first autonomous local AI platform and interactive terminal cockpit powered by Ollama and OpenAI-compatible inference backends (vLLM, LocalAI, text-generation-webui).**

`locaLLM` transforms raw local models into production-ready autonomous capabilities: an **Interactive AI Assistant**, a **Multi-Step ReAct Coding Agent**, **24/7 Telegram & WhatsApp Bots**, **Isolated Project Workspaces**, and a **Hardware-Aware Model Manager**.

---

## ⚡ Quickstart (Get Running in 60 Seconds)

### 1. Prerequisites
- **Python**: 3.9+ (Python 3.10–3.13 recommended)
- **Local Inference Engine**: [Ollama](https://ollama.com/) running locally (`http://127.0.0.1:11434`) or any OpenAI-compatible server (e.g. vLLM, LocalAI)
- **Node.js**: 18+ *(optional, required only for WhatsApp bot QR pairing via Baileys)*

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/MFathan7/locaLLM-python.git
cd locaLLM-python

# (Recommended) Create and activate a Python virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Register 'locallm' global CLI command in editable mode
pip install -e .
```

### 3. Updating locaLLM to Latest Version
If you already installed `locaLLM` and want to update to the latest features, run:
```bash
# 1. Pull latest updates from GitHub
git pull origin main

# 2. Update dependencies and refresh CLI installation
pip install -r requirements.txt
pip install -e .

# 3. Verify health & connectivity
locallm status
```

### 4. Essential Commands
```bash
# 1. Launch the Interactive TUI Dashboard
locallm

# 2. Start an Interactive Chat session with Smart Auto-Routing
locallm chat --model auto

# 3. Run an Autonomous Agent task (files, shell, web, GitHub releases)
locallm agent --task "Analyze README.md and summarize project architecture"

# 4. Run an Autonomous Agent task with custom max reasoning steps
locallm agent --task "Fetch latest Ollama releases and compare versions" --max-steps 30

# 5. Check GPU VRAM and model compatibility
locallm models
```

---

## ✨ Feature Overview

### 🤖 Interactive Assistant & Bot Runners
- **Interactive Assistant Cockpit**: Rich session welcome card with detected capabilities (Tools, Vision, Reasoning), active workspace, context limits, and keyboard shortcuts (`Enter` send, `Ctrl+J` newline).
- **Telegram Bot (`locallm telegram`)**: 24/7 bot daemon with per-user conversation memory, user ID whitelisting, Markdown-to-HTML formatting, and photo/document delivery tools.
- **WhatsApp Bot (`locallm whatsapp`)**: Terminal QR code pairing via Baileys bridge, multi-user memory, phone whitelist, group chat support, and automatic 15-digit LID resolution.
- **Cross-Channel Parity**: Uniform context telemetry (`• Context: 2,681/8,192 (32.7%) • Speed: 37.8 tok/s`) and slash commands (`/stats`, `/model`, `/clear`, `/help`) across CLI, Telegram, and WhatsApp.

### 🧠 Workspace Persona Engine (`AGENTS.md`) & Proactive Research
- **Customizable Persona Directives**: Every workspace contains its own `AGENTS.md` file defining how the model thinks, responds, and uses tools.
- **Auto-Scaffolding**: Newly created workspaces automatically inherit a production-grade persona template with zero manual configuration.
- **Decoupled Backend Prompts**: Core Python scripts remain clean and minimal; all system prompts and directives live directly in editable markdown.
- **Proactive Web Research**: Local models are instructed to never claim ignorance or lack of real-time data for unfamiliar entities, protocols, or products.
- **Turn 1 Refusal Interceptor**: If a model hesitates or admits a lack of knowledge on turn 1 (e.g. for niche enterprise tools), `locaLLM` automatically intercepts and nudges the model to execute `search_web` before synthesizing the final answer.

### 🛠️ Autonomous ReAct Agent & Native Tools
- **Multi-Step Autonomous Loop**: Executes up to 25 continuous tool steps (`create_directory`, `write_file`, `read_file`, `list_directory`, `execute_command`, `search_web`, `fetch_web`).
- **Granular Permission Policies**: Configure mutating tool policies per session:
  - `ask`: Interactively prompts user authorization (`Allow Once`, `Always Allow`, `Deny`).
  - `always_allow`: Fully hands-free autonomous execution for agent tasks.
  - `deny`: Read-only execution mode blocking all filesystem modifications.
- **Silent Tool Execution**: Tools execute quietly behind dynamic spinners with live completion badges (`✔ Written file`, `✔ Searched web`) without polluting conversation history.
- **Resilient Tool Recovery**: Automatically detects and executes tool calls even if a model outputs raw or markdown-wrapped JSON in the text stream.

### 🎯 Intelligent Auto Model Router
- **5-Dimension Intent Classification**: Evaluates prompts in real time across `CODING`, `REASONING`, `VISION`, `TOOLS`, and `FAST_CHAT`.
- **Parameter Capacity Priority**: Prefers higher-capacity models (`14B` > `7B` > `3B`) for heavy development and reasoning workloads.
- **Sticky Routing (Anti-Swap Protection)**: Retains the currently loaded GPU model if it satisfies prompt requirements, preventing expensive disk I/O and latency spikes.
- **VRAM Hardware Guard**: Checks KV cache footprints and model weights against actual free GPU memory, automatically falling back to the next fitting model to prevent system freeze or CPU spillover.

### 🗂️ Zero-Bleed Workspaces & Skills
- **Strict Context Isolation**: Each project workspace (`~/.locallm/workspaces/<name>/`) contains isolated `knowledge/`, `skills/`, and `sessions/`. No cross-contamination across projects.
- **Drop-In Markdown Knowledge**: Drop `.md` or `.txt` reference files, API specs, and runbooks directly into workspace directories.
- **Pure-Python GitHub Skill Installer**: Install agent skills from any GitHub repo (`locallm workspace install org/repo --skill name`) with automatic bloat filtering (`.git`, tests, binaries).

### 🔌 Modular Plugin System
- **Dynamic Tool Injection**: Register custom tools, database connectors, and external APIs using declarative `plugin.json` manifests without touching core code.
- **Three-Tier Discovery**: Loads plugins with priority: Project-Local (`<cwd>/plugins/`) > Workspace-Isolated > Global (`~/.locallm/plugins/`).
- **Safety Policy Enforcement**: Any plugin tool declaring `"mutating": true` automatically adheres to interactive permission policies.

### 💻 Developer Cockpit & Theming
- **5 High-Contrast Themes**: Switch between **Cyber Neon** (`⚡`), **Tokyo Night** (`◈`), **Monokai** (`★`), **Matrix** (`λ`), and **Nordic Frost** (`❄`).
- **Bracket Frame Architecture**: Clean open-body response cards (`┌─ ⟦model⟧` top, `└─ ⟦telemetry⟧` bottom) eliminating vertical side pipes (`│`), ensuring **100% clean copy-pasting** from any terminal.
- **Monospace-Pure TUI**: Monospace-safe text choices without emojis in Questionary menus, guaranteeing pixel-perfect alignment on Windows Terminal and CMD.

### 📊 Precision VRAM Hardware Sizing
- **GQA Channel Awareness**: Calculates exact KV cache sizes based on physical KV head geometry rather than query heads, avoiding 4×–8× memory over-estimation.
- **Sliding Window Attention (SWA)**: Binds local attention layers for hybrid architectures (e.g. Gemma 4, Mistral), preventing false spillover warnings on large context windows.
- **Dynamic Classification**: Automatically evaluates models as `100% GPU (FIT)` or `SPILLOVER`.

---

## 🧭 TUI Menu Hierarchy

Launch `locallm` with no arguments to enter the interactive terminal dashboard:

```text
Main Menu:
  ├── Assistant             -> Standalone interactive chat with live tool execution
  ├── Workspaces            -> Isolated environments: Switch, Create, Edit AGENTS.md, Delete, Back
  ├── Integrations          -> Channels & external runners
  │     ├── Telegram        -> 24/7 Telegram bot: Start, Configure Token, Whitelist, Back
  │     ├── WhatsApp        -> WhatsApp bot: Start, Configure Whitelist, Clear Session, Back
  │     ├── Agent & Auto    -> Autonomous Agent: Run Task, Toggle Auto-Approve, Back
  │     └── Back            -> Return to Main Menu
  ├── Model Manager         -> Model management per platform
  │     ├── Ollama          -> List models, VRAM sizing, Set Active, Pull, Delete, Back
  │     ├── [Custom Plat]   -> OpenAI-compatible platform models, Set Active, Delete, Back
  │     ├── Add Platform    -> Register new OpenAI-compatible backend
  │     └── Back            -> Return to Main Menu
  ├── Plugins               -> Modular integrations: Inspect, Toggle, Scaffold, Back
  ├── Services              -> Server daemon lifecycle per platform
  │     ├── Ollama          -> Status, Start Daemon, Stop Daemon, Configure Endpoint, Back
  │     ├── [Custom Plat]   -> Status, Set Active, Configure Endpoint/Key, Delete, Back
  │     ├── Add Platform    -> Register new OpenAI-compatible platform
  │     └── Back            -> Return to Main Menu
  ├── Settings              -> Global parameters (Backend, Temperature, Context, Theme, Reset)
  └── Exit                  -> Unload GPU VRAM and terminate cleanly
```

---

## 💻 CLI Command Reference

`locaLLM` provides a comprehensive command-line interface for scripting, terminal shortcuts, and headless server environments:

### Core Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| `locallm` | Open interactive TUI dashboard | `locallm` |
| `locallm chat` | Launch interactive assistant session | `locallm chat --model auto` |
| `locallm agent` | Run autonomous ReAct agent loop | `locallm agent --task "Scaffold FastAPI app"` |
| `locallm run "<prompt>"` | Single-shot prompt execution (piping / scripts) | `locallm run "Summarize commit history"` |
| `locallm models` | Inspect models and physical VRAM fit | `locallm models` |
| `locallm status` | View backend connectivity, GPU VRAM & active model | `locallm status` |
| `locallm telegram` | Start 24/7 Telegram bot integration daemon | `locallm telegram` |
| `locallm whatsapp` | Start WhatsApp bot integration runner (QR pair) | `locallm whatsapp` |
| `locallm start [target]` | Start Ollama background server process | `locallm start ollama` |
| `locallm stop [target]` | Terminate local service processes and unload VRAM | `locallm stop ollama` |

### Workspace Management

| Command | Description | Example |
| :--- | :--- | :--- |
| `locallm workspace list` | List all installed workspaces | `locallm workspace list` |
| `locallm workspace use <name>` | Switch active workspace globally | `locallm workspace use dev-project` |
| `locallm workspace create <name>` | Create a new isolated workspace | `locallm workspace create audit -d "Security audit"` |
| `locallm workspace instruct "<text>"` | Set custom workspace instructions | `locallm workspace instruct "Focus on OWASP Top 10"` |
| `locallm workspace add-knowledge <title>` | Add reference markdown doc to workspace | `locallm workspace add-knowledge api --file ./spec.md` |
| `locallm workspace add-skill <name>` | Add custom agent skill manually | `locallm workspace add-skill review --file ./review.md` |
| `locallm workspace install <source>` | Install skill from GitHub repository | `locallm workspace install org/repo --skill audit` |
| `locallm workspace delete <name>` | Delete an inactive custom workspace | `locallm workspace delete audit` |

### Custom Inference Platforms & Plugins

| Command | Description | Example |
| :--- | :--- | :--- |
| `locallm platform list` | List registered inference platforms | `locallm platform list` |
| `locallm platform add <name>` | Register an OpenAI-compatible platform | `locallm platform add vllm -e http://127.0.0.1:8000/v1` |
| `locallm platform use <name>` | Switch active backend platform | `locallm platform use vllm` |
| `locallm platform remove <name>` | Remove custom platform configuration | `locallm platform remove vllm` |
| `locallm plugin list` | List installed plugins and tools | `locallm plugin list` |
| `locallm plugin enable <name>` | Enable a modular plugin | `locallm plugin enable sqlite_db` |
| `locallm plugin disable <name>` | Disable a modular plugin | `locallm plugin disable sqlite_db` |
| `locallm plugin create <name>` | Scaffold a starter plugin template | `locallm plugin create my_tool` |

---

## 💬 Slash Commands & Chat Ergonomics

During interactive chat (`locallm chat`), Telegram bot, or WhatsApp bot conversations, use standard slash commands or natural language keywords:

| Slash Command | Natural Keywords | Description |
| :--- | :--- | :--- |
| `/stats` | `stats`, `context`, `telemetry` | Renders active model, context tokens used/limit, speed (`tok/s`), and history depth. |
| `/model` | `model` | Displays active model and features. Use `/model auto` to toggle dynamic routing. |
| `/clear` | `/reset`, `clear`, `reset`, `start fresh` | Wipes current conversation history and clears memory. |
| `/help` | `help` | Displays command and keyword reference guide. |
| `/sessions` | `sessions` | Lists, switches, or deletes saved session histories for the active workspace. |
| `/back` | `back` | Returns to the main menu without terminating the application. |
| `/exit` | `exit`, `quit` | Unloads GPU VRAM cleanly (`keep_alive: 0`) and exits. |

---

## 🧠 Workspace Persona Engine (`AGENTS.md`)

Each workspace has a dedicated `AGENTS.md` file stored at:
```text
~/.locallm/workspaces/<workspace_name>/AGENTS.md
```

### 1. Progressive Persona Resolution
When compiling the prompt context, `locaLLM` resolves directives in strict order of precedence:
1. **Active Workspace**: `~/.locallm/workspaces/<name>/AGENTS.md` (or `SOUL.md`)
2. **Global Custom Directives**: `~/.locallm/AGENTS.md`
3. **Default Built-in Directives**: `DEFAULT_WORKSPACE_AGENTS_MD` template
4. **Project Repository Rules**: Loaded automatically from `<cwd>/AGENTS.md` or `CLAUDE.md` under `[Project Architecture & Rules]`.

### 2. Proactive Web Search & Refusal Interception
Traditional local models often emit canned refusals (e.g., *"I don't have information about X"* or *"My knowledge cutoff is..."*) when asked about unfamiliar entities, niche enterprise software, or real-time news.

`locaLLM` fixes this with a two-layer guarantee:
- **Cognitive Directives**: The persona explicitly mandates proactive tool usage (`search_web`) on the very first turn whenever encountering unfamiliar entities or missing data.
- **Autonomous Refusal Interceptor**: If the model still emits an admission of ignorance on turn 1 instead of calling tools, `locaLLM` intercepts the turn, issues an in-place nudge with the query, runs `search_web` silently, and returns verified factual data.

---

## 🛠️ Built-in Native Tools

Native tools execute silently behind high-contrast spinners (`▘▀▝▐▗▄▖▌`) and output real-time completion status:

| Tool | Action Description | Safety & Highlights |
| :--- | :--- | :--- |
| `create_directory` | Creates directories recursively | Scaffolds parent directories automatically anywhere on the filesystem. |
| `write_file` | Writes or overwrites files | Auto-creates parent directories; outputs written character count. |
| `read_file` | Reads file contents | UTF-8 safe with line numbers and token budget guards. |
| `list_directory` | Lists directory contents | Folder-first listing (`[DIR]` before `[FILE]`); expands aliases (`~`, `downloads`, `desktop`). |
| `execute_command` | Executes shell commands | Adheres strictly to permission policy (`ask`, `always_allow`, `deny`). |
| `search_web` | Searches the web | Multi-engine support (`auto`, `duckduckgo`, `bing`, `custom`) to prevent network blocking. |
| `fetch_web` | Fetches webpage text | Markdown converter; direct raw `README.md` download for GitHub URLs. |
| `get_weather` | Real-time weather reporting | Plain-text weather via wttr.in with Windows console charmap safety. |
| `get_current_time` | System clock | Formatted local time, day, and date. |
| `list_skills` | Skill discovery | Discovers all skills across workspace and project root. |
| `read_skill` | Skill reader | Loads full skill markdown instructions on demand. |

---

## 🎨 Theme Engine

Customize your terminal aesthetic on the fly via `Settings -> UI Theme`:

| Theme Key | Box Style | Glyph | Prompt Prefix | AI Output Badge | Palette Accents |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `cyber_neon` *(Default)* | Double `╔══╗` | `⚡` | `▲ You:` | `⚡ locaLLM ❯` | Electric Cyan & Neon Magenta |
| `tokyo_night` | Rounded `╭──╮` | `◈` | `◆ You:` | `◈ locaLLM ›` | Night Purple & Deep Sky Blue |
| `monokai` | Heavy `┏━━┓` | `★` | `■ You:` | `★ locaLLM »` | Retro Yellow & Fresh Mint |
| `matrix` | Square `┌──┐` | `λ` | `>>> You:` | `λ locaLLM $` | Hacker Phosphor Green |
| `nordic_frost` | Rounded `╭──╮` | `❄` | `• You:` | `❄ locaLLM ›` | Polar Cyan & Platinum Silver |

---

## 📐 Precision VRAM Sizing Formula

`locaLLM` replaces naive fixed buffers with exact Grouped-Query Attention (GQA) and Sliding Window Attention (SWA) channel calculations:

```text
Channels        = Layers × KV_Heads × Head_Dim
Bytes_per_Token = 2 × Channels × Precision_Bytes  (FP16 = 2B, FP8/Q8 = 1B)
KV_Cache_GB     = (Context_Tokens × Bytes_per_Token) / (1024³)
Usable_VRAM     = Total_GPU_VRAM - OS_Display_Usage
Total_VRAM      = Model_Weights_GB + KV_Cache_GB + CUDA_Overhead (~0.6 GB)
Max_Context     = (Usable_VRAM - Model_Weights - CUDA_Overhead) × 1024³ / Bytes_per_Token
```

### Classification
- 🟢 **100% GPU (FIT)**: `Total_VRAM ≤ Usable_VRAM` (Headroom ≥ 0). Runs entirely in GPU VRAM at maximum generation speed.
- 🔴 **SPILLOVER**: `Total_VRAM > Usable_VRAM`. Context or weights partially offload to CPU RAM, degrading tokens/second.

---

## ⚙️ Configuration Reference

Configuration is stored in `~/.locallm/config.json` (`%USERPROFILE%\.locallm\config.json` on Windows):

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
  "default_model": "auto",
  "temperature": 0.7,
  "context_window": 8192,
  "system_prompt": "You are locaLLM, an autonomous, highly capable, and disciplined local AI assistant.",
  "active_workspace": "default",
  "ui_theme": "cyber_neon",
  "web_search_engine": "auto",
  "plugins_enabled": true,
  "telegram_token": "",
  "telegram_allowed_users": [],
  "whatsapp_enabled": false,
  "whatsapp_allowed_numbers": [],
  "whatsapp_session_dir": "",
  "agent_auto_approve_commands": false,
  "agent_permission_policy": "ask"
}
```

---

## 🧪 Testing & Verification

Run the test suite to verify code quality and platform compatibility:

```bash
# Discover and run all unit tests
python -m unittest discover -s tests -p "test_*.py"
```

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
