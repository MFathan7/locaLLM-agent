# locaLLM

```text
       █░░ █▀█ █▀▀ ▄▀█ █░░ █░░ █▀▄▀█
       █▄▄ █▄█ █▄▄ █▀█ █▄▄ █▄▄ █░▀░█
              ✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ  ✦
```

> **Developer-first autonomous local AI platform, interactive terminal cockpit, and modern Liquid Glass Web UI powered by Ollama and OpenAI-compatible inference backends (vLLM, LocalAI, text-generation-webui).**

`locaLLM` transforms raw local models into production-ready autonomous capabilities: an **Interactive AI Assistant**, a **Modern Liquid Glass Web UI**, a **Multi-Step ReAct Coding Agent**, **24/7 Telegram & WhatsApp Bots**, **Isolated Project Workspaces**, and a **Hardware-Aware Model Manager**.

---

## ⚡ Quickstart (Get Running in 60 Seconds)

### 1. Prerequisites
- **Python**: 3.9+ (Python 3.10-3.13 recommended)
- **Local Inference Engine**: [Ollama](https://ollama.com/) running locally (`http://127.0.0.1:11434`) or any OpenAI-compatible server (e.g. vLLM, LocalAI)
- **Node.js**: 18+ and npm (for the Web UI and WhatsApp bot pairing)

### 2. Installation

#### Automated Installation (Linux & macOS)
Run the automated installer script which auto-detects your OS (including Arch Linux, Ubuntu/Debian, Fedora, macOS), bootstraps the Python virtual environment (`.venv`), installs all dependencies, and configures the `locallm` CLI command:

```bash
# 1. Clone repository & enter directory
git clone https://github.com/MFathan7/locaLLM-python.git
cd locaLLM-python

# 2. Make installer executable & run
chmod +x install.sh
./install.sh
```

> **Arch Linux Tip**: Ensure basic Python and virtualenv packages are present:
> ```bash
> sudo pacman -S python python-pip python-virtualenv
> ```

#### Manual Installation (Windows, Linux, macOS)
```bash
# Clone the repository
git clone https://github.com/MFathan7/locaLLM-python.git
cd locaLLM-python

# Create and activate a Python virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies and register 'locallm' CLI command
pip install -r requirements.txt
pip install -e .
```

### 3. Launching the Web UI Cockpit (Vite + React)
`locaLLM` includes a modern, high-performance Web UI synchronized 1:1 with the CLI engine:

```bash
# 1. Go to the frontend directory
cd frontend

# 2. Install frontend dependencies (first run)
npm install

# 3. Start the development server with the backend bridge
npm run dev
```
Open **`http://localhost:5173`** in your browser. All configuration changes, workspaces, and chat histories created in the Web UI are directly shared with the CLI.

### 4. Updating locaLLM to Latest Version
If you already installed `locaLLM` and want to update to the latest features, run:
```bash
# 1. Pull latest updates from GitHub
git pull origin main

# 2. Update dependencies and refresh CLI installation
pip install -r requirements.txt
pip install -e .

# 3. Update frontend dependencies if needed
cd frontend && npm install && cd ..

# 4. Verify health & connectivity
locallm status
```

### 5. Essential Commands
```bash
# 1. Launch the Interactive Main Menu with Live Telemetry Header
locallm

# 2. Launch the Real-Time VRAM & System Monitor HUD
locallm top

# 3. Start an Interactive Chat / Coding Agent session with Smart Auto-Routing & Typing Effect
locallm chat --model auto

# 4. Launch the Autonomous Coding Agent interactively (or with --task for scripts)
locallm agent
locallm agent --task "Analyze README.md and summarize project architecture"

# 5. Start OpenAI-Compatible HTTP API Gateway (/v1/chat/completions)
locallm serve --port 8080

# 6. Check GPU VRAM and model compatibility
locallm models
```

---

## ✨ Feature Overview

### 🌐 Modern Liquid Glass Web UI (Vite + React + Tailwind)
- **Apple Liquid Glass Aesthetic**: Inspired by modern macOS and iOS glass design, featuring translucent glassmorphism surfaces (`backdrop-filter: blur(24px)`), gradient specular highlights, soft sheen curves, and an animated blurred Aurora mesh background.
- **Direct 1:1 Synchronization with CLI**: The Web UI communicates through a native local bridge with zero data silos. System prompts, sampling temperature, active model, custom OpenAI platforms, agent policies, and workspace chat histories are shared bidirectionally with the CLI in real time (`~/.locallm/config.json` and `~/.locallm/workspaces/`).
- **Dual-Theme Architecture**: Sleek dark mode and crisp high-contrast light mode with deep slate typography (`text-slate-950 font-bold`), ensuring zero text wash-out and complete legibility across all surfaces.
- **Clean Reasoning & Trace Filtering**: Strips intermediate `<think>...</think>` tokens, raw tool JSON dumps, and search queries from final responses while displaying a pulsing `Thinking and reasoning...` indicator while reasoning is underway.
- **Collapsible Sources Side Panel**: Automatically extracts external web citations and search references into branded source cards with domain favicons, accessible via a right-hand sliding panel.
- **One-Click Document Export (`.doc`)**: Export any assistant response directly into a styled Microsoft Word document with headings, tables, code blocks, and citation appendices.
- **Refined Tables & Hover Copy Icon**:
  - Horizontal-only grid lines (no vertical lines) with centered, bold column headers and no outer perimeter borders.
  - Hover-activated copy icon button positioned beside the table that copies the entire table with headers in both Markdown and HTML.
- **Tactile Copy Action Buttons**: One-click copy buttons with animated hover tooltips on both assistant responses and user message bubbles.
- **Lazy "New Chat" Creation**: Clicking New Chat enters an empty draft state without creating empty session files on disk until the first message is sent.
- **Intelligent Auto Chat Title Generation**:
  - Instant heuristic title extraction stripping conversational filler words (*"tolong buatkan"*, *"can you help me"*, etc.).
  - Non-blocking asynchronous AI title synthesis running in the background to name conversations by user goal.
- **Adaptive Header Navigation**: Top header search icon hides when the sidebar is visible and animates in when collapsed, maintaining smooth spring transitions with zero animation gaps.
- **Rich Markdown, Code Highlighting & Image Lightbox**:
  - Syntax-highlighted code blocks with language tags and one-click copy.
  - Inline image rendering with full-screen zoom lightbox modal.
- **High-Performance Conversation Search**:
  - Instant keyboard shortcut access (`Ctrl+F` or `Cmd+K` or header search icon).
  - Debounced input (120ms) for instantaneous 60fps keystrokes.
  - Contextual snippet extraction displaying ~120 characters centered around matches instead of unconstrained text dumps.
  - Smooth asynchronous chat opening with zero main-thread locking.
- **Centered Floating Scroll-to-Bottom Button**: Dynamic scroll detector displaying a sleek circular icon-only button in the bottom-center of the viewport whenever scrolled up.
- **Dynamic Model & Platform Picker**:
  - Model list displays model name on top and platform name (*Ollama*, *OpenAI*, or custom platforms) underneath.
  - Select active inference platform (native local Ollama or custom remote OpenAI-compatible servers like vLLM / iForte-GPU).
  - Model dropdowns re-query available models with 60-second in-memory caching and request timeout guards.
- **Dynamic Plus Action Menu**:
  - Upload file attachments.
  - Toggle real-time Web Search on/off for models that support it.
  - Toggle Autonomous Agent Tools on/off dynamically per prompt.

### 🖥️ Real-Time Telemetry Header Banner
- **Live System & Hardware Cockpit**: The Unicode header banner at the top of every screen automatically displays real-time hardware telemetry:
  - **Service & Ping**: Backend connectivity and live network ping latency (`● Service: ONLINE (1.8ms)`).
  - **GPU & VRAM Meter**: Real-time VRAM allocation bar with exact headroom (`▰ VRAM: [█░░░░░░░░░] 1.6/12.0 GB (13%) (+10.3G free)`), GPU core compute load, and operating temperature (`8% load • 39°C`).
  - **Host RAM & CPU**: Host system memory usage bar and active CPU utilization with core count.
  - **Resident Models**: Direct visibility into models actively occupying GPU memory via `/api/ps`.

### ⚡ Live Thinking Animation & Typing Effect
- **Live Reasoning Stream**: Native real-time thought tracking for reasoning models (DeepSeek-R1, QwQ) with live timer and token count (`💭 Thought Process (3.2s)`), resolving cleanly into `✔ Thought for 3.2s` before streaming the markdown answer.
- **Automatic Live Typing Effect**: Real-time typewriter cursor (`▌`) and smooth emission cadence while generating tokens. Code blocks auto-close on the fly to maintain clean syntax highlighting while the cursor is typing.
- **Real-Time Stream Speedometer**: Dynamic live footer while emitting tokens (`▘ Emitting: 142 tokens • 42.1 tok/s • 3.4s • VRAM: 7.2/12.0 GB`), powered by high-contrast square snake spinners that smoothly settle into the final bracket footer.
- **Monospace Alignment & Anti-Slop**: Pure text menus and Rich formatting designed specifically for Windows terminal monospace fonts with zero alignment breakage.

### 📊 Live System Monitor HUD (`locallm top` / `/top`)
- **Full-Screen Hardware Telemetry**: 1-second auto-refreshing HUD tracking GPU VRAM, compute load, temperature, host CPU, and RAM with non-blocking exit (`q` or `Enter`).
- **Universal Slash Command**: Access the Live Monitor on-the-fly anytime from inside chat sessions with `/top` or `/monitor`.

### 🚀 OpenAI-Compatible HTTP API Gateway (`locallm serve`)
- **Universal OpenAI Endpoint**: Expose your local models through an OpenAI-standard HTTP service (`/v1/chat/completions` and `/v1/models`), compatible out of the box with **Cursor**, **Continue.dev**, **Claude Code**, **LibreChat**, **Open-WebUI**, and **LangChain**.
- **Smart Port Collision Fallback**: If the default port (e.g. `8080`) is already bound by another process, `locaLLM` automatically detects the conflict and finds the next available port (`8081..8090`).
- **Optional Bearer Token Authentication**: Secure your API gateway with custom keys (`--api-key <secret>` or `LOCALLM_API_KEY`).
- **Server-Sent Events (SSE) Streaming**: Chunked token emission matching the OpenAI SSE streaming protocol with live usage metrics.
- **Header Telemetry Badge & Lifecycle**: Displayed dynamically in the telemetry banner (`API :8080`), with complete daemon control via CLI (`locallm serve`) or `Settings -> API Server Gateway`.

### 🤖 Unified Autonomous Coding Agent & Interactive Assistant
- **Consolidated Coding Agent Cockpit**: Interactive assistant (`locallm chat` and `locallm agent`) combines full conversational memory with multi-step autonomous execution (`MAX_TOOL_STEPS = 25`).
- **Direct Execution Authority**: The agent autonomously scaffolds directories, creates and refactors files, executes shell commands, inspects project repositories, and queries web documentation.
- **Granular Permission Policies**: Configured globally in `Settings -> Agent Permission Policy`:
  - `always_allow`: Fully hands-free autonomous coding and terminal execution.
  - `ask`: Interactive approval prompt (`Allow Once`, `Always Allow`, `Deny`) before mutating actions.
  - `deny`: Read-only execution mode blocking all filesystem modifications and shell execution.
- **Telegram Bot (`locallm telegram`)**: 24/7 bot daemon with per-user conversation memory, user ID whitelisting, Markdown-to-HTML formatting, and photo/document delivery tools.
- **WhatsApp Bot (`locallm whatsapp`)**: Terminal QR code pairing via Baileys bridge, multi-user memory, phone whitelist, group chat support, and automatic 15-digit LID resolution.
- **Cross-Channel Parity**: Uniform context telemetry (`• Context: 2,681/8,192 (32.7%) • Speed: 37.8 tok/s`) and slash commands (`/stats`, `/model`, `/clear`, `/sessions`, `/help`) across CLI, Telegram, and WhatsApp.

### 🧠 Workspace Persona Engine (`AGENTS.md`) & Proactive Research
- **Customizable Persona Directives**: Every workspace contains its own `AGENTS.md` file defining how the model thinks, responds, and uses tools.
- **Auto-Scaffolding**: Newly created workspaces automatically inherit a production-grade persona template with zero manual configuration.
- **Decoupled Backend Prompts**: Core Python scripts remain clean and minimal; all system prompts and directives live directly in editable markdown.
- **Proactive Web Research**: Local models are instructed to never claim ignorance or lack of real-time data for unfamiliar entities, protocols, or products.
- **Turn 1 Refusal Interceptor**: If a model hesitates or admits a lack of knowledge on turn 1 (e.g. for niche enterprise tools), `locaLLM` automatically intercepts and nudges the model to execute `search_web` before synthesizing the final answer.

### 🛠️ Modular Tool Registry & Silent Tool Execution
- **Modular Tool Architecture (`locallm/core/tools/`)**: Tools are decoupled into domain packages (`filesystem.py`, `web.py`, `system.py`, `messaging.py`, `ui.py`) and dynamically registered via `@tool` decorators.
- **Explicit JSON Schema & Typing**: Declarations enforce JSON Schema metadata, parameter typing, and mutating permission classification (`is_mutating: bool`).
- **Dynamic Truncation & Pagination**: Content-heavy tools (file reading, web fetching) support clean sliding chunking (`offset`, `max_chars`) to prevent context exhaustion and latency spikes.
- **Smart Path Resolution & Boundary Sandboxing**: Resolves filesystem aliases (`~`, `downloads`, `desktop`, `%USERPROFILE%`) and enforces directory boundary isolation in restricted or messaging modes.
- **Silent Tool Execution**: Tools execute quietly behind dynamic spinners with live completion badges (`✔ Written file`, `✔ Searched web`) without polluting conversation history.
- **Resilient Tool Recovery**: Automatically detects and executes tool calls even if a model outputs raw or markdown-wrapped JSON in the text stream.

### 🎯 Intelligent Auto Model Router
- **5-Dimension Intent Classification**: Evaluates prompts in real time across `CODING`, `REASONING`, `VISION`, `TOOLS`, and `FAST_CHAT`.
- **Parameter Capacity Priority**: Prefers higher-capacity models (`14B` > `7B` > `3B`) for heavy development and reasoning workloads.
- **Sticky Routing (Anti-Swap Protection)**: Retains the currently loaded GPU model if it satisfies prompt requirements, preventing expensive disk I/O and latency spikes.
- **VRAM Hardware Guard**: Checks KV cache footprints and model weights against actual free GPU memory, automatically falling back to the next fitting model to prevent system freeze or CPU spillover.

### 🌐 Model Context Protocol (MCP) Multi-Server Support
- **Multi-Connection Architecture**: Connect to multiple MCP servers concurrently (`filesystem`, `github`, `postgres`, `sqlite`, remote APIs).
- **Transport Flexibility**: Native support for **`stdio`** (subprocesses via `npx`, `python`, `node`, `uvx`) and **`sse`** (remote HTTP/SSE streams).
- **Zero External Bloat**: High-performance, zero-conflict JSON-RPC 2.0 client built directly on standard Python libraries and HTTPX.
- **Cross-Platform & Standard Compatible**: Standard `mcp_servers.json` configuration compatible with Claude Desktop and Cursor.
- **Unified Tool Dispatch & Namespacing**: Discovered MCP tools are dynamically exposed to Chat, Autonomous ReAct Agent, Telegram Bot, and WhatsApp Bot with collision-free namespacing (`mcp__<server>__<tool>`).
- **Access Control & Privilege Gating**: Flag servers or individual tools as `privileged` to restrict them to authorized administrator callers only.
- **Interactive TUI & CLI**: Manage servers with `locallm mcp list`, `locallm mcp test <name>`, `locallm mcp enable/disable <name>`, or the interactive wizard in `Integrations -> Model Context Protocol (MCP)`.

### 🗂️ Zero-Bleed Workspaces, Skills & Isolated Sessions
- **Strict Context Isolation**: Each project workspace (`~/.locallm/workspaces/<name>/`) contains isolated `knowledge/`, `skills/`, and `sessions/`. No cross-contamination across projects.
- **Drop-In Markdown Knowledge**: Drop `.md` or `.txt` reference files, API specs, and runbooks directly into workspace directories.
- **Pure-Python GitHub Skill Installer**: Install agent skills from any GitHub repo (`locallm workspace install org/repo --skill name`) with automatic bloat filtering (`.git`, tests, binaries).
- **Multi-Select Skill Deletion**: Cleanly batch-delete installed skills using interactive checkbox selection (`Delete Skill(s)`).
- **Isolated Chat Session Management**: Slash command `/sessions` and delete prompts exclusively list native chat sessions, isolating external Telegram, WhatsApp, and API channels. Clearing chat history never deletes bot histories.

### 🔌 Modular Plugin System
- **Dynamic Tool Injection**: Register custom tools, database connectors, and external APIs using declarative `plugin.json` manifests without touching core code.
- **Three-Tier Discovery**: Loads plugins with priority: Project-Local (`<cwd>/plugins/`) > Workspace-Isolated > Global (`~/.locallm/plugins/`).
- **Safety Policy Enforcement**: Any plugin tool declaring `"mutating": true` automatically adheres to interactive permission policies.

### 💻 Developer Cockpit & Theming
- **5 High-Contrast Themes**: Switch between **Cyber Neon** (`⚡`), **Tokyo Night** (`◈`), **Monokai** (`★`), **Matrix** (`λ`), and **Nordic Frost** (`❄`).
- **Bracket Frame Architecture**: Clean open-body response cards (`┌─ ⟦model⟧` top, `└─ ⟦telemetry⟧` bottom) eliminating vertical side pipes (`│`), ensuring **100% clean copy-pasting** from any terminal.
- **Monospace-Pure TUI**: Monospace-safe text choices without emojis in Questionary menus, guaranteeing pixel-perfect alignment on Windows Terminal and CMD.

### 📊 Precision VRAM Hardware Sizing
- **GQA Channel Awareness**: Calculates exact KV cache sizes based on physical KV head geometry rather than query heads, avoiding 4x-8x memory over-estimation.
- **Sliding Window Attention (SWA)**: Binds local attention layers for hybrid architectures (e.g. Gemma 4, Mistral), preventing false spillover warnings on large context windows.
- **Dynamic Classification**: Automatically evaluates models as `100% GPU (FIT)` or `SPILLOVER`.

---

## 🧭 Interface & Navigation

When launching `locallm`, the terminal displays the real-time telemetry header banner followed by the interactive main menu:

```text
╔════════════════════════════ ✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ  ✦ ════════════════════════════╗
║                                                                             ║
║                        █░░ █▀█ █▀▀ ▄▀█ █░░ █░░ █▀▄▀█                        ║
║                        █▄▄ █▄█ █▄▄ █▀█ █▄▄ █▄▄ █░▀░█                        ║
║                                                                             ║
║  ● Service: ONLINE (1.8ms)             ⚡ Endpoint: http://127.0.0.1:11434  ║
║  (Ollama)                                                                   ║
║  ◆ Model: deepseek-r1:8b                        ★ Features: Tools, Vision   ║
║  ■ GPU: RTX 4070 (8% load • 39°C)         ▰ VRAM: [█░░░░░░░░░] 1.6/12.0 GB  ║
║                                                        (13%) (+10.3G free)  ║
║  ◈ Host: RAM: [███░░░░░] 13.2/31.9         ● VRAM Resident: Standby (Idle)  ║
║  GB (41%) • CPU: 13.2% (16c)                                                ║
║  ▸ Workspace: default                        ⚡ Cyber Neon  •  ✦ 2 Plugins  ║
║                                                                             ║
╚═════════════════════════════════════════════════════════════════════════════╝
```

```text
Main Menu:
  ├── Assistant             -> Interactive coding agent with multi-step tools, session persistence, & typing effect
  ├── Workspaces            -> Isolated environments: Switch, Create, Edit AGENTS.md, Skills, Delete, Back
  ├── Integrations          -> Channels & external bot runners
  │     ├── Telegram        -> 24/7 Telegram bot: Start, Configure Token, Whitelist, Back
  │     ├── WhatsApp        -> WhatsApp bot: Start, Configure Whitelist, Clear Session, Back
  │     ├── Model Context Protocol (MCP) -> Multi-server MCP manager: Test, Add, Enable/Disable, Remove, Back
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
  ├── Settings              -> Global parameters (Backend, API Gateway, Theme, Temperature, Context, Permission Policy, Search)
  └── Exit                  -> Unload GPU VRAM and terminate cleanly
```

---

## 💻 CLI Command Reference

`locaLLM` provides a comprehensive command-line interface for scripting, terminal shortcuts, and headless server environments:

### Core Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| `locallm` | Open interactive main menu with real-time hardware telemetry header | `locallm` |
| `locallm top` | Launch auto-refreshing real-time system & VRAM monitor HUD | `locallm top --refresh 0.5` |
| `locallm chat` | Launch interactive coding assistant session with typing effect | `locallm chat --model auto` |
| `locallm agent` | Launch interactive coding agent (or with `--task` for headless execution) | `locallm agent` / `locallm agent --task "Scaffold FastAPI app"` |
| `locallm serve` | Start OpenAI-compatible HTTP API Gateway server (`/v1/chat/completions`) | `locallm serve --port 8080 --host 0.0.0.0` |
| `locallm run "<prompt>"` | Single-shot prompt execution (piping / scripts) | `locallm run "Summarize commit history"` |
| `locallm models` | Inspect models and physical VRAM fit | `locallm models` |
| `locallm status` | View backend connectivity, GPU VRAM & active model | `locallm status` |
| `locallm telegram` | Start 24/7 Telegram bot integration daemon | `locallm telegram` |
| `locallm whatsapp` | Start WhatsApp bot integration runner (QR pair) | `locallm whatsapp` |
| `locallm start [target]` | Start Ollama background server process | `locallm start ollama` |
| `locallm stop [target]` | Terminate local service processes and unload VRAM | `locallm stop ollama` |

### API Gateway Server (`locallm serve`)

| Option / Flag | Description | Default |
| :--- | :--- | :--- |
| `--port`, `-p` | Port number to bind HTTP server | `8080` (auto-detects and increments if busy) |
| `--host`, `-H` | Host IP address to bind | `127.0.0.1` |
| `--api-key`, `-k` | Optional Bearer authentication secret key | `None` (open access) |
| `--workspace`, `-w` | Target workspace context for persona and tools | Active workspace |
| `--model`, `-m` | Override default model served | Active model |
| `--no-auto-port` | Disable automatic collision fallback | `False` |

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
| `/top` | `/monitor`, `top`, `monitor` | Opens real-time system & VRAM monitor HUD on the fly from inside chat. |
| `/stats` | `stats`, `context`, `telemetry` | Renders active model, context tokens used/limit, speed (`tok/s`), and history depth. |
| `/model` | `model` | Displays active model and features. Use `/model auto` to toggle dynamic routing. |
| `/new` | `new session` | Archives current conversation and starts a fresh, isolated chat session. |
| `/sessions` | `sessions` | Lists, switches, or deletes saved chat session histories for the active workspace. |
| `/delete` | `/del`, `/rm` | Interactive dialog to delete the current session, specific saved chats, or all chat sessions. |
| `/clear` | `/reset`, `clear`, `reset` | Wipes current conversation history and clears memory in place. |
| `/system` | `system` | View and dynamically customize the system prompt on the fly. |
| `/help` | `help` | Displays command and keyword reference guide. |
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
  "search_provider": "auto",
  "server_enabled": false,
  "server_host": "127.0.0.1",
  "server_port": 8080,
  "server_api_key": null,
  "plugins_enabled": true,
  "telegram_token": "",
  "telegram_allowed_users": [],
  "whatsapp_enabled": false,
  "whatsapp_allowed_numbers": [],
  "whatsapp_session_dir": "",
  "agent_auto_approve_commands": false,
  "agent_permission_policy": "ask",
  "agent_max_steps": 25
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
