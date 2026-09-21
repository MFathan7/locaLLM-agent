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
- **Intelligent Auto Model Router & Dynamic Intent Dispatch**:
  - Automatically evaluates incoming user prompts in real time and classifies intent across 5 core dimensions: `CODING`, `REASONING`, `VISION`, `TOOLS`, and `FAST_CHAT`.
  - **Parameter Capacity Priority**: Evaluates candidate models by parameter capacity descending (`14b` > `7b` > `3b` > `1.5b`), directing software development tasks to specialized coder models.
  - **Sticky Routing (Anti-Thrashing Protection)**: Avoids costly GPU model swaps if the currently loaded model is already capable of handling the intent, protecting disk I/O and latency.
  - **Hardware & VRAM Safety Guard**: Automatically cross-references model weight footprints, context window KV cache requirements (accounting for GQA and Sliding Window Attention), and CUDA runtime buffers against idle GPU VRAM. If a larger model exceeds VRAM, the router seamlessly falls back to the next fitting candidate without downgrading to a generalist.
  - **Channel-Clean Telemetry**: Displays dynamic routing badges in interactive CLI sessions (`⚡ Auto Router: <intent> -> <model> (<reason>)`), while logging cleanly to the server terminal during Telegram and WhatsApp bot runs without cluttering user messages.
- **Model Manager & Precision Architecture-Aware VRAM Sizing**:
  - Automatic GPU detection (NVIDIA VRAM via `pynvml` / `nvidia-smi`) and system RAM inspection.
  - Exact VRAM sizing formula accounting for Grouped-Query Attention (GQA) channels and hybrid Sliding Window Attention (SWA), accurately classifying models as `100% GPU` (FIT) or `SPILLOVER`.
  - Pull new models from the Ollama registry with real-time console download progress.
  - Delete unused models from Ollama or custom OpenAI-compatible platforms with confirmation to reclaim disk space.
  - Multi-platform support: Seamlessly register, inspect, and switch between Ollama and OpenAI-compatible custom backends.
- **Service Lifecycle Manager (`locaLLM start / stop`)**:
  - Full manual control to start and stop background Ollama server processes or monitor custom platforms without silent auto-spawning.
- **Interactive Assistant & Autonomous Coding Agent (`locaLLM chat` / `locaLLM agent`)**:
  - Streaming Markdown responses in real time with syntax-highlighted code blocks.
  - **Autonomous Multi-Step ReAct Loop**: Continuous action execution where the LLM plans, executes tools, inspects observations, and self-terminates (up to 25 steps) with completion synthesis.
  - **Granular Permission Policy (`always_allow`, `ask`, `deny`)**: Mutating actions (`write_file`, `create_directory`, `execute_command`) prompt for user confirmation (`Allow Once`, `Always Allow`, `Deny`) or run fully autonomous.
  - **Persistent Live Real-Time Reports**: Immediate console feedback (`✔ Created directory`, `✔ Written file (X chars)`, `✔ Executed command`) right as each tool finishes.
  - **Resilient Fallback Tool Call Extraction**: Automatically recovers and executes tool calls even when local engines emit them as raw or markdown JSON in the content stream.
  - **Multiline Input Ergonomics**: `Enter` to send, `Ctrl+J` or `Ctrl+Down` for newlines without triggering Windows CMD fullscreen toggling.
- **Integrations & Bot Runners**:
  - **Telegram (`locaLLM telegram`)**: Run your local model as a 24/7 Telegram bot featuring multi-user memory, allowed user ID whitelist, native Telegram tools (photo sending, document delivery, animated dice), and automatic markdown-to-HTML formatting.
  - **WhatsApp (`locaLLM whatsapp`)**: Run your local model as a WhatsApp bot featuring terminal QR code pairing, multi-turn memory, allowed phone number whitelisting, automatic 15-digit LID-to-phone number resolution, group chat support with quoted replies, and silent tool execution.
  - **Autonomous Agent (`locaLLM agent`)**: Multi-step CLI automation runner with native tool calling and auto-approval policies.
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
  │     ├── Ollama          -> List models, VRAM fit check, Set Active, Pull, Delete, Back
  │     ├── [Custom Platform] -> Platform models, Set Active, Delete, Back
  │     ├── Add Custom Platform -> Register new OpenAI-compatible platform
  │     └── Back            -> Return to Main Menu
  ├── Services              -> Server daemon lifecycle per platform
  │     ├── Ollama          -> Status, Start Server, Stop Server, Configure Endpoint, Back
  │     ├── [Custom Platform] -> Status, Set Active, Configure Endpoint/Key, Delete, Back
  │     ├── Add Custom Platform -> Register new OpenAI-compatible platform
  │     └── Back            -> Return to Main Menu
  ├── Settings              -> Global inference parameters only (Backend, Temp, Context Window, Prompt, Reset)
  └── Exit                  -> Unload VRAM and terminate application
```

---

## Intelligent Auto Model Router

`locaLLM` features an integrated **Auto Model Router** that dynamically inspects every incoming user prompt, categorizes computational and reasoning requirements, and selects the optimal local model installed on your system.

### 1. Multi-Signal Intent Classification
Prompts are analyzed in real time across 5 core intent dimensions:

| Intent Category | Trigger Signals & Patterns | Target Model Archetype | Example Candidates |
| :--- | :--- | :--- | :--- |
| **`CODING`** | Code blocks (` ``` `), stack traces, programming languages (Python, Rust, C++, JS, SQL), refactoring, debugging | Dedicated coder models with code-syntax fine-tuning | `qwen2.5-coder`, `deepseek-coder`, `codellama` |
| **`REASONING`** | Analytical problem-solving, math proofs, step-by-step logic, architectural analysis, complex planning | High-parameter or dedicated reasoning / thinking models | `deepseek-r1`, `qwq`, `hermes3`, `llama3` |
| **`VISION`** | Image analysis, OCR, visual document inspection, screenshots | Multimodal vision models | `llava`, `minicpm-v`, `qwen-vl` |
| **`TOOLS`** | Time, directories, files, weather forecasts, shell commands, web research | Models with native function-calling & JSON schema support | `gemma4`, `hermes3`, `qwen2.5`, `mistral` |
| **`FAST_CHAT`** | Greetings, short Q&A, casual chat, quick summaries, rephrasing | Lightweight, fast-response models (3B–8B parameters) | `llama3.2:3b`, `qwen2.5:7b`, `phi3` |

### 2. Sticky Routing (Anti-Swap Hardware Protection)
Swapping large models in and out of GPU VRAM incurs substantial disk I/O, memory reallocation, and initial generation latency.
- To prevent unnecessary model thrashing, `locaLLM` implements **Sticky Routing**: if the currently loaded model is already equipped to handle the detected intent (e.g. it has tools support for a tool prompt, or high reasoning capability), the router keeps the active model.
- A model swap is only triggered when another candidate possesses a significantly higher suitability score (score difference > 15 points).

### 3. VRAM Safety Guard & SWA Context Window Scaling
Before any model is selected by the router, `locaLLM` evaluates its total memory footprint against actual idle GPU VRAM:
- **Spillover Prevention**: If a candidate model's required VRAM (weights + KV cache + CUDA overhead) exceeds available GPU VRAM, it is disqualified to avoid system freeze or slow CPU offloading. The router automatically falls back to the highest-scoring candidate that safely runs 100% in VRAM.
- **Sliding Window Attention (SWA) Awareness**: For hybrid models like Gemma 4 or Mistral, local attention layers are capped at the model's sliding window size (e.g. 1,024 tokens), preventing false spillover rejections on large context limits.

### 4. How to Enable Auto Routing
- **Interactive TUI**: Navigate to `Model Manager` -> `Ollama` (or Custom Platform) -> `Set Active Model` -> select `Auto (Smart Router)`.
- **In-Chat Command**: Type `/model auto` during any interactive chat session.
- **CLI Flags**: Pass `--model auto` to any CLI command:
  ```powershell
  locaLLM chat --model auto
  locaLLM run "Explain quantum annealing in detail" --model auto
  locaLLM agent --model auto --task "Review python files in src"
  ```
- **Bot Integrations**: When running `locaLLM telegram` or `locaLLM whatsapp`, auto router decisions are logged cleanly on the server console:
  ```text
  [Router] Routed prompt (Intent: CODING) -> qwen2.5-coder:7b (Dedicated coding model)
  ```
  Chat users receive direct model responses without technical router metadata cluttering their conversations.

---

## Precision Architecture-Aware VRAM Sizing

Unlike naive calculators that estimate fixed memory buffers, `locaLLM` computes exact inference memory requirements using Grouped-Query Attention (GQA) channel geometry and hybrid Sliding Window Attention (SWA) awareness.

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   VRAM SIZING & KV CACHE ARCHITECTURE                                  │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  Channels        = Layers × KV_Heads × Head_Dim                                                        │
│  Bytes/Token     = 2 × Channels × Precision_Bytes  (Precision: FP16=2B, FP8/Q8=1B)                     │
│  KV Cache (GB)   = (Context_Tokens × Bytes_per_Token) / (1024³)                                        │
│  Usable VRAM     = Total_GPU_VRAM - OS_Display_Usage                                                   │
│  Total VRAM      = Model_Weights_GB + KV_Cache_GB + CUDA_Overhead (~0.6 GB)                            │
│  Max Context     = (Usable_VRAM - Model_Weights - CUDA_Overhead) × 1024³ / Bytes_per_Token             │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. KV Cache Footprint Formula

Modern architectures (Llama 3, Qwen 2.5, Gemma, Mistral) utilize Grouped-Query Attention (GQA) where multiple query heads share a single key-value head pair. Memory per token is calculated from physical KV channel geometry:

```text
Channels        = Layers × KV_Heads × Head_Dim
Bytes_per_Token = 2 × Channels × Precision_Bytes
```

For models with standard global attention across all layers:
```text
KV_Cache_GB = (Context_Tokens × Bytes_per_Token) / (1024³)
```

For hybrid Sliding Window Attention (SWA) architectures (e.g. Gemma 4, Mistral):
```text
                  Layers
KV_Cache_GB = [    ∑    (KV_Heads × Head_Dim × 2 × Precision_Bytes × min(Tokens, Window_l)) ] / 1024³
                 l = 1
```

- **Precision Options**: `2 bytes` (FP16 / BF16 default) or `1 byte` (FP8 / Q8 quantized KV cache).
- **GQA Channel Scaling**: Evaluates physical KV heads (`num_key_value_heads`) rather than query heads, preventing 4×–8× over-estimation of KV cache.
- **Sliding Window Attention (SWA)**:
  - Models with alternating local/global attention only allocate full context tokens to global layers.
  - Local layers are bounded by `Window_l = 1,024` tokens.
  - *Real-World Impact*: At 65,536 context, standard FP16 KV cache would require ~40+ GB. With Gemma 4 SWA awareness (40 local layers, 8 global layers), the KV cache is accurately calculated at only **1.31 GB**, reflecting actual real-world GPU allocation.

### 2. Usable GPU VRAM

Available inference VRAM is determined dynamically by querying the GPU driver via `pynvml` or `nvidia-smi`:

```text
Usable_VRAM = Total_GPU_VRAM - OS_Display_Usage
```

### 3. Total Required VRAM & CUDA Runtime Overhead

```text
Total_VRAM = Model_Weights_GB + KV_Cache_GB + CUDA_Overhead_GB
```

Where `CUDA_Overhead_GB ≈ 0.6 GB` covers the CUDA runtime context, scratchpad buffers, and activation memory.

### 4. Compatibility Classification

| Status | Condition | Generation Behavior |
| :--- | :--- | :--- |
| 🟢 **100% GPU (FIT)** | `Total_VRAM ≤ Usable_VRAM` (Headroom ≥ 0) | The model runs completely on GPU with optimal generation throughput. |
| 🔴 **SPILLOVER** | `Total_VRAM > Usable_VRAM` | Context or weights will partially offload to CPU RAM, degrading token generation throughput. |

### 5. Maximum Safe Context Window

Computes the exact context token ceiling before the model spills into system RAM:

```text
Max_Context_Tokens = (Usable_VRAM - Model_Weights_GB - CUDA_Overhead_GB) × 1024³ / Bytes_per_Token
```

---

## Built-in Native Tools & Smart Filesystem

All tools run silently behind a minimalist rotating square snake spinner (`▘▀▝▐▗▄▖▌`) during interactive chat, agent loops, Telegram, and WhatsApp sessions, with persistent real-time completion reports (`✔`) rendered in the terminal.

| Tool Name | Purpose | Key Features & Safeguards |
| :--- | :--- | :--- |
| **`create_directory`** | Directory creation | Recursively creates directories anywhere on the filesystem, automatically scaffolding parent folders as needed. |
| **`write_file`** | File generation & writing | Writes or overwrites text files anywhere on the system with automatic parent directory creation and character count metrics. |
| **`read_file`** | File content inspection | Reads UTF-8 text files with line numbering, length safeguards, and workspace bounds checking. |
| **`list_directory`** | Filesystem inspection | Folder-first listing (directories `[DIR]` prioritized over `[FILE]`) with total counts. Automatically expands smart aliases (`downloads`, `desktop`, `documents`, `~`, `%USERPROFILE%`). |
| **`execute_command`** | Terminal automation | Executes shell commands within the current environment, adhering strictly to configured permission policy (`always_allow`, `ask`, `deny`). |
| **`fetch_web`** | Web research | Fetches web pages as clean text/markdown. Directly resolves and downloads raw `README.md` files for GitHub repository URLs. |
| **`get_weather`** | Weather forecasts | Plain-text weather reporting via wttr.in with Windows console charmap encoding protection (ASCII/Latin degree normalization). |
| **`get_current_time`** | Real-time clock | Returns formatted system local time, day, and date. |
| **`get_current_directory`** | Working directory | Returns active workspace directory path. |
| **`list_skills`** | Skill discovery | Discovers and lists all installed agent skills across active workspace and project root (`.locallm/skills/`, `.agents/skills/`, `skills/`). |
| **`read_skill`** | Skill execution | Reads and loads full specialized skill markdown instructions on demand. |

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
You can also enable the smart auto router or specify a model and workspace on launch:
```powershell
# Run with smart dynamic model routing based on prompt intent:
locaLLM chat --model auto

# Or pin to an explicit model and isolated workspace:
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
# Run with active default model:
locaLLM run "Write a Python function to compute Fibonacci numbers with memoization"

# Run with intelligent auto model router:
locaLLM run "Optimize this SQL query for PostgreSQL 16" --model auto
```

### 7. Inspect Installed Models & VRAM Compatibility
```powershell
locaLLM models
```
Inspects all local models, evaluates VRAM requirements against physical GPU memory using the precision GQA & SWA formula, and allows setting the active model (including `Auto (Smart Router)`), pulling new models, or deleting unused models.

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
| `/model` | `model` | Displays the currently active model and detected capabilities (Tools, Vision, Reasoning). In interactive assistant, use `/model auto` to engage dynamic smart routing, or `/model <model_name>` to pin a specific model. |
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
  "default_model": "auto",
  "temperature": 0.7,
  "context_window": 8192,
  "system_prompt": "You are locaLLM, a helpful, fast, and intelligent local AI assistant.",
  "active_workspace": "default",
  "telegram_token": "YOUR_TELEGRAM_BOT_TOKEN",
  "telegram_allowed_users": [],
  "whatsapp_enabled": false,
  "whatsapp_allowed_numbers": ["628123456789"],
  "whatsapp_session_dir": "",
  "agent_auto_approve_commands": false,
  "agent_permission_policy": "ask"
}
```

All settings can be configured interactively through the `Settings`, `Workspaces`, `Integrations`, and `Services` menus in the TUI, or via the `locaLLM config` CLI command.
