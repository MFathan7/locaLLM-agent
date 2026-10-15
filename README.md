# locaLLM

```text
       █░░ █▀█ █▀▀ ▄▀█ █░░ █░░ █▀▄▀█
       █▄▄ █▄█ █▄▄ █▀█ █▄▄ █▄▄ █░▀░█
              ✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ  ✦
```

> **Developer-first autonomous local AI platform, interactive terminal cockpit, and modern Liquid Glass Web UI powered by Ollama and OpenAI-compatible inference backends (vLLM, LocalAI, text-generation-webui).**

`locaLLM` transforms raw local models into production-ready autonomous capabilities: an **Interactive AI Assistant & Open Code Cockpit**, a **Modern Liquid Glass Web UI**, a **Visual LocaLLM Agent Workflow Studio (Signal Flow DAG with Live Pipeline Execution)**, a **Multi-Agent Coordination Team (Supervisor, Coder, Researcher, Auditor)**, an **Agentic Coding Engine with Surgical File Patching & AST Syntax Guard**, a **Zero-Dependency Vector Knowledge Base & Hybrid RAG Engine**, a **Dual-Tier Long-Term Memory Engine**, an **OpenAI & n8n Automation Bridge (Sync & Async Webhooks)**, **24/7 Telegram & WhatsApp Bots**, **Zero-Bleed Project Workspaces**, and a **Hardware-Aware Model Manager**.

---

## ⚡ Quickstart (Get Running in 60 Seconds)

### 1. Prerequisites
- **Python**: 3.9+ (Python 3.10-3.13 recommended)
- **Local Inference Engine**: [Ollama](https://ollama.com/) running locally (`http://127.0.0.1:11434`) or any OpenAI-compatible server (e.g. vLLM, LocalAI)
- **Node.js**: 18+ and npm (for the Web UI and WhatsApp bot pairing)

### 2. Installation

#### Automated Installation (Windows)
Run the automated Windows installer script which auto-detects Python, creates the `.venv` virtual environment, installs dependencies, and configures global CLI runners:

```powershell
# In PowerShell or Command Prompt:
.\install.bat

# Or directly in PowerShell:
.\install.ps1
```

#### Automated Installation (Linux & macOS)
Run the automated installer script which auto-detects your OS (including Arch Linux, Ubuntu/Debian, Fedora, macOS), bootstraps the Python virtual environment (`.venv`), installs all dependencies, and configures the `locallm` CLI command:

```bash
# 1. Clone repository & enter directory
git clone https://github.com/username/locaLLM.git
cd locaLLM

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
git clone https://github.com/username/locaLLM.git
cd locaLLM

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

# 3. Start an Interactive Chat / Open Code session with Smart Auto-Routing & Typing Effect
locallm chat --model auto

# 4. Launch the Autonomous Coding Agent interactively (Single ReAct or Multi-Agent Team)
locallm agent
locallm agent --task "Analyze README.md and summarize project architecture"

# 5. Launch Hierarchical Multi-Agent Coordination directly
locallm agent --multi
locallm agent --multi --task "Refactor auth middleware and verify test coverage"

# 6. Start OpenAI & n8n Compatible HTTP API Gateway (/v1/chat/completions)
locallm serve --port 8080

# 7. Check GPU VRAM and model compatibility
locallm models

# 8. Start Ollama and LocaLLM API server in the background
locallm start

# 9. Stop background services cleanly
locallm stop
```

---

## ✨ Feature Overview

### 🌐 Modern Liquid Glass Web UI (Vite + React + Tailwind)
- **Apple Liquid Glass Aesthetic**: Inspired by modern macOS and iOS glass design, featuring translucent glassmorphism surfaces (`backdrop-filter: blur(24px)`), gradient specular highlights, soft sheen curves, and an animated blurred Aurora mesh background.
- **Direct 1:1 Synchronization with CLI**: The Web UI communicates through a native local bridge with zero data silos. System prompts, sampling temperature, active model, custom OpenAI platforms, agent policies, and workspace chat histories are shared bidirectionally with the CLI in real time (`~/.locallm/config.json` and `~/.locallm/workspaces/`).
- **Dual-Theme Architecture**: Sleek dark mode and crisp high-contrast light mode with deep slate typography (`text-slate-950 font-bold`), ensuring zero text wash-out and complete legibility across all surfaces.
- **Multi-Session Background AI Execution**: Full concurrency across conversation sessions. Users can freely switch between chats or start new drafts while the AI is actively reasoning or generating in another session. Background streaming continues writing directly to the session without interruption or UI thread lockup.
- **Response Ready Toast Notifications & Sidebar Status Indicators**:
  - Floating Liquid Glass notification toast displays when a background AI generation finishes, featuring an instant one-click **"Open"** action button to jump directly into the finished chat.
  - Native desktop notifications (via Web Notifications API) alert users when multitasking in other browser tabs or external applications.
  - Real-time sidebar activity indicator (pulsing dot) displays on sessions actively generating in the background, accompanied by an unread completion badge until visited.
- **Real-Time Stream Cancellation & Dynamic Stop Button**:
  - The send button dynamically morphs into an accessible **Stop Button** (with a square icon) whenever the AI is in reasoning or token generation mode.
  - Clicking Stop immediately triggers an `AbortController` cancellation signal to cut model inference on demand, cleanly preserving all previously streamed response content without displaying error banners.
- **Wave-to-Triangle Thinking Spinner**:
  - GPU-accelerated CSS animation providing rich visual feedback during reasoning phases.
  - Three dots wave along a horizontal line, converge into a precise equilateral triangle, spin 360 degrees on their centroid, and expand back into a line, accompanied by semibold status labels (*"Thinking..."*, *"Generating..."*, *"Searching..."*, *"Running Python..."*) with smooth fade transitions.
- **Event-Driven Reasoning States & Zero-Leak CoT**: High-level execution state streaming (`routing`, `thinking_start`, `thinking_end`, `tool_start`, `tool_end`, `response_start`, `response_token`, `done`). Internal reasoning is kept strictly internal to the engine, displaying clean generic status indicators (*"Thinking..."*, *"Searching..."*, *"Running Python..."*, *"Generating..."*) without leaking raw thoughts or fake reasoning tokens.
- **Clean Reasoning & Trace Filtering**: Strips intermediate `<think>...</think>` and `<thought>...</thought>` blocks from final response bubbles and chat titles, keeping the output clean and uncluttered.
- **Zero-Delay Streaming Web Search**: Connects instantly via SSE and emits real-time status chunks while executing web queries, synthesizing verified findings with markdown citations (`[Source Title](URL)`) and auto-populating the sources side panel.
- **Collapsible Sources Side Panel**: Automatically extracts external web citations and search references into branded source cards with domain favicons, accessible via a right-hand sliding panel.
- **One-Click Document Export (`.doc`)**: Export any assistant response directly into a styled Microsoft Word document with headings, tables, code blocks, and citation appendices.
- **Refined Tables & Hover Copy Icon**:
  - Horizontal-only grid lines (no vertical lines) with centered, bold column headers and no outer perimeter borders.
  - Hover-activated copy icon button positioned beside the table that copies the entire table with headers in both Markdown and HTML.
- **Tactile Copy Action Buttons**: One-click copy buttons with animated hover tooltips on both assistant responses and user message bubbles.
- **Lazy "New Chat" Creation**: Clicking New Chat enters an empty draft state without creating empty session files on disk until the first message is sent.
- **Intelligent Auto Chat Title Generation**:
  - Instant heuristic title extraction stripping conversational filler words (*"tolong buatkan"*, *"can you help me"*, etc.).
  - Thought-aware asynchronous AI title synthesis running in the background that waits for reasoning blocks to finish before naming conversations by user goal, ensuring zero leaked `<think>` tags in session titles.
- **Adaptive Header Navigation**: Top header search icon hides when the sidebar is visible and animates in when collapsed, maintaining smooth spring transitions with zero animation gaps.
- **Seamless Canvas CodeBlocks**:
  - Multi-language syntax-highlighted code canvas with uniform dark surface across header and body, zero distracting borders or grid lines, bold language headers, and customized dark horizontal scrollbars.
  - Sticky header pinning at `top: 0` during vertical code scroll without mid-air floating gaps.
  - Icon-only copy button with instant green checkmark visual feedback and universal fallback (`document.execCommand` + textarea) for restricted clipboard environments.
- **Collapsible Thought Process Accordion**:
  - Deep reasoning traces (`<think>` / `<thought>`) are automatically parsed into an interactive expandable thought accordion above the answer. While reasoning is underway, status states stream dynamically; once the answer tokens begin generating, the accordion collapses automatically into a clean header, keeping internal reasoning accessible without cluttering the final output.
- **Floating Header with Full-Screen Message Scroll**:
  - Translucent model picker and theme controls float gracefully with passthrough pointer events, allowing conversation messages to glide smoothly all the way to the top edge of the browser viewport.
- **Image Lightbox & Universal File Preview Modal**:
  - Inline image rendering with full-resolution zoom lightbox modal.
  - Dedicated interactive modal for previewing attached PDFs, code scripts with syntax highlighting, and text files before or after sending.
- **High-Performance Conversation Search**:
  - Instant keyboard shortcut access (`Ctrl+F` or `Cmd+K` or header search icon).
  - Debounced input (120ms) for instantaneous 60fps keystrokes.
  - Contextual snippet extraction displaying ~120 characters centered around matches instead of unconstrained text dumps.
  - Smooth asynchronous chat opening with zero main-thread locking.
- **Centered Floating Scroll-to-Bottom Button**: Dynamic scroll detector displaying a sleek circular icon-only button in the bottom-center of the viewport whenever scrolled up.
- **Top-Left Header Model & Backend Picker**:
  - Repositioned cleanly to the top-left header of the chat viewport, displaying the active model name and inference backend (*Ollama*, *OpenAI*, or custom platforms) with an instant dropdown switcher.
  - Automatically re-queries available models with 60-second in-memory caching and connection timeout guards.
  - **Instant Platform Synchronization & Zero-Leak VRAM Release**: Switching between Ollama and custom platforms (e.g. remote vLLM, iForte-GPU, LocalAI) automatically updates the active backend and immediately evicts Ollama models from local VRAM (`keep_alive: 0`), releasing gigabytes of GPU memory instantly.
  - **Safe Dynamic Model Routing**: Selecting `'auto'` dynamically resolves to the platform default or first installed model prior to dispatch, eliminating `"model not found"` errors.
- **Model-Aware "Thinking" Mode Toggle**:
  - Dynamically verifies whether the active model supports reasoning/thinking via `/api/models/check-thinking` (inspecting model architecture, capabilities, and naming conventions like DeepSeek-R1, QwQ, Gemma, or Qwen reasoning variants).
  - An interactive **"Thinking" button** appears in the chat toolbar when compatible, allowing users to toggle reasoning tokens on or off per message turn.
- **Plus Menu Context & Tool Selector**:
  - Expandable **"+" action button** with transparent idle styling and numeric badge indicators when tools or web search are enabled.
  - Dedicated popover menu to toggle **Web Search** and **Workspace Agent Tools** without cluttering the input textarea.
- **Dynamic Multiline Chat Input**:
  - Smooth vertical expansion as prompts grow, keeping action controls aligned along the bottom toolbar.
- **Universal Clipboard Paste & Multi-File Attachment System (Up to 5 Files)**:
  - **Instant Clipboard Paste (Ctrl+V)**: Paste any file type directly into the chat input from your clipboard, including screenshots, images, PDFs, text documents, code scripts (`.py`, `.ts`, `.json`, etc.), and spreadsheets.
  - **Drag-and-Drop & File Picker**: Drop files anywhere on the chat input card or select via the Plus menu.
  - **Interactive File Previews & Tooltips**: File chips display format-specific icons with hover tooltips and one-click preview modals.
  - **Multi-Turn Context Retention**: Extracted text content stays in context across all subsequent turns so the model never forgets document contents in follow-up queries.
- **Dynamic Contextual Greetings**:
  - Native `Intl.DateTimeFormat` context aware greetings tailored to time-of-day and day-of-week (*"Can I help you on this Friday morning, Fathan?"*), providing a warm and natural entrance for every new conversation without generic filler.
- **AI Disclaimer Header**:
  - Non-intrusive safety and responsibility disclaimer above the chat input box (*"LocaLLM can stumble sometimes. Stay sharp and double-check key info."*).
- **Real-Time Temporal Grounding**:
  - Injects live real-world date and time into workspace context so the model always knows current time and date without hallucinations.
- **Refined Workspace Management Modal**:
  - Apple Liquid Glass modal architecture with fluid tab navigation (General & Skills).
  - Dynamic workspace icon picker with automatic theme-aware contrast validation.
  - Native toggle switch for **Workspace Auto-Memory Extraction**, allowing granular control over per-project episodic memory learning.
  - Auto-sorted chat sessions by last activity timestamp for effortless history tracking.
- **Visual Agent Workflow Studio Navigation**:
  - Dedicated "Visual Agent Workflow" button positioned neatly above Workflows in the desktop sidebar, featuring an outbound arrow icon (`ArrowUpRight`) that opens the visual DAG studio at `/workflow` in a new tab without disruptive decorative backgrounds.
- **Collapsible Workspace Accordion**:
  - Compact sidebar navigation with an automatic collapse/expand toggle when workspace counts exceed 5 projects, preserving vertical real estate.
- **Resilient React Error Boundary**:
  - Built-in crash protection wrapping the application root with a Liquid Glass recovery screen, diagnostic details, and one-click session restore, completely eliminating white-screen state collapses.

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
- **Universal OpenAI Endpoint**: Expose your local models through an OpenAI-standard HTTP service (`/v1/chat/completions` and `/v1/models`), compatible out of the box with standard tools and clients such as **Cursor**, **Continue.dev**, **LibreChat**, **Open-WebUI**, and **LangChain**.
- **Model Thinking Capability Endpoint**: Dedicated `/api/models/check-thinking` (and `/v1/models/check-thinking`) endpoint for inspecting whether specific models natively support reasoning/thinking modes, with `think: true/false` parameter passthrough.
- **Smart Port Collision Fallback**: If the default port (e.g. `8080`) is already bound by another process, `locaLLM` automatically detects the conflict and finds the next available port (`8081..8090`).
- **Optional Bearer Token Authentication**: Secure your API gateway with custom keys (`--api-key <secret>` or `LOCALLM_API_KEY`).
- **Server-Sent Events (SSE) Streaming**: Chunked token emission matching the OpenAI SSE streaming protocol with live usage metrics.
- **Header Telemetry Badge & Lifecycle**: Displayed dynamically in the telemetry banner (`API :8080`), with complete daemon control via CLI (`locallm serve`) or `Settings -> API Server Gateway`.

### 🤝 Multi-Agent Coordination & Smart Capability Routing
- **Hierarchical Supervisor-Specialist Architecture**: Combines a lead Supervisor with targeted specialist agents to tackle complex, multi-stage engineering tasks:
  - **Supervisor / Orchestrator**: Analyzes objectives, decomposes projects into ordered sub-tasks, assigns execution to the optimal specialist, and aggregates final deliverables.
  - **Coder Specialist**: Generates surgical patches, writes modular functions, and implements logic with exact language syntax.
  - **Research Specialist**: Explores filesystems, indexes documentation, extracts knowledge base chunks, and fetches technical references.
  - **Auditor / Tester Specialist**: Runs syntax checkers, executes unit tests, reviews unified code diffs, and inspects security vulnerabilities.
- **Dynamic Multidimensional Capability Profiler (`profiler.py`)**:
  - Dynamically profiles every locally installed model across 5 critical dimensions: `coding_score`, `reasoning_score`, `context_score`, `tool_score`, and `speed_score`.
  - Completely eliminates rigid, hardcoded model name checks. Any model family (Qwen 2.5/3.5, Gemma 4, GLM-4.6, Hermes 3, Llama 3, DeepSeek, etc.) is evaluated dynamically and assigned to its strongest specialist role.
- **Shared Blackboard State Architecture (`blackboard.py`)**:
  - Solves the local VRAM context explosion problem: rather than stuffing every specialist's entire context history into a single bloated prompt, each specialist operates within an isolated context window.
  - Specialists exchange findings, architectural blueprints, file diffs, test logs, and task statuses through an in-memory, thread-safe Shared Blackboard.
- **CLI Visual Orchestration HUD (`cli_ui.py`)**:
  - Real-time progress rendering in the terminal cockpit showing the active specialist, execution step counts, and task handoffs (`Supervisor -> Coder: implement handler`, `Supervisor -> Auditor: verify syntax`).
- **Flexible Invocation Modes**:
  - Launch via interactive console menu: `Autonomous Agent -> Multi-Agent Team (Multi)`.
  - Launch via CLI flag: `locallm agent --multi` (or headless with `locallm agent --multi --task "..."`).
  - Launch from chat session: `/multi <task>` or `/team <task>`.

### 🔀 LocaLLM Agent Workflow Studio (Signal Flow Visual DAG)
- **Signal Flow Architectural Canvas**:
  - Full-screen visual node orchestration studio accessible at `/workflow` (or directly via the sidebar button in a new tab).
  - **4-Phase Sequential Journey**: Horizontal timeline demarcating pipeline progression across the canvas:
    - *Phase 1: Intake & Context*: Captures user objectives, cron timers, or inbound messaging triggers.
    - *Phase 2: Planning & Policy Governance*: Supervisor decomposition coupled with safety circuit breakers and human approval gates.
    - *Phase 3: Specialist Execution*: Autonomous specialist execution (Coder Specialist, Researcher, Writer, and Critic / QA).
    - *Phase 4: Evidence & Delivery*: Central state sink consolidating unified diffs, test logs, physical file exports, and messaging dispatchers.
  - **5-Lane Structured Taxonomy**:
    - `ui`: User objective intake and external triggers (cron schedules, messaging webhooks).
    - `agent`: Supervisor planner, specialist agent runtime, and model routers.
    - `policy`: Safety guards, permission barriers, and quality gates (If/Else branching).
    - `tools`: Execution capabilities (terminal commands, filesystem operators, live web and API fetchers).
    - `evidence`: Blackboard state sink, document exporters, and messaging dispatchers.
- **2-Port Topology Architecture (Dual-Port Paradigm)**:
  - **Main Flow (Horizontal)**: Standard pipeline progression connecting `in` (left) to `out` (right) ports along the execution timeline.
  - **Sub-Nodes & Resources (Vertical)**: Auxiliary specialists, dynamic model routers, tool runners, and blackboard state sinks connect directly into the Supervisor coordinator via `sub-in` (bottom) ports, creating clean, readable multi-agent coordination topologies without cluttering the main flow.
- **Production-Grade Real Use-Case Presets**:
  - **1. Full-Stack Code Audit & Auto-Refactor (QA Loop Pattern)**:
    - *Main Flow*: `User Objective Input` -> `Task Decomposer` -> `Supervisor / Coordinator` -> `Critic / QA Agent` -> `Quality Gate (If/Else)` -> (`Chat & Artifact Output` on pass | Loopback to `Supervisor` with retry budget on fail).
    - *Sub-Nodes*: `Dynamic Model Router`, `Blackboard Hub`, `Coder Agent` (connected to `Filesystem` & `Shell Runner`).
    - *Deliverables*: Unified diffs and verified code refactoring logs.
  - **2. Autonomous Market Intelligence & Strategy Digest (Consensus Pattern)**:
    - *Main Flow*: `User Objective Input` -> `Supervisor / Coordinator` -> `Critic / QA Agent` -> `Document Exporter` -> `Messaging Dispatcher`.
    - *Sub-Nodes*: `Researcher Agent` (with `Web Search`), `Analyst Agent` (with `Memory / Blackboard`), `Writer Agent`.
    - *Deliverables*: Comprehensive intelligence briefing saved to `docs/market_intelligence_report.md` and dispatched to Telegram.
  - **3. Automated Incident Response & Self-Healing**:
    - *Main Flow*: `Messaging Inbound Trigger` -> `Supervisor / Coordinator` -> `Quality Gate (If/Else)` -> `Subprocess / Shell Runner` -> `Messaging Dispatcher`.
    - *Sub-Nodes*: `Dynamic Model Router`, `Blackboard Hub`, `Auditor Specialist`.
    - *Deliverables*: Automated incident triage, remediation script execution, and status alert broadcast.
  - **4. Auto Grab Al-Qur'an & Tafsir (Live equran.id API v2 Integration)**:
    - *Main Flow*: `Messaging Trigger` (Telegram / WhatsApp) -> `Supervisor / Coordinator` -> `Researcher Agent` -> `Writer Agent` -> `Critic / QA Agent` -> `Document Exporter` -> `Messaging Dispatcher`.
    - *Sub-Nodes*: `Dynamic Model Router`, `Blackboard Hub`, `Web Search` (equran.id API bridge).
    - *Highlights*: Connects live to `https://equran.id/api/v2/surat/{nomor}`, formats authentic Arabic calligraphy typography with verse markers, extracts Indonesian translation and surah metadata, embeds high-fidelity Murottal recitation audio streaming (Syaikh Misyari Rasyid Al-Afasi), exports clean Markdown to `docs/quran_surah_output.md` with instant browser auto-download, and sends rich HTML notifications to Telegram.
  - **5. Scheduled System Audit & Human Approval Gate**:
    - *Main Flow*: `Schedule Trigger` (Daily Cron) -> `Supervisor / Coordinator` -> `Chat & Artifact Output` (Action Required Notice) -> `Quality Gate (If/Else)` -> `Coder Agent` -> `Document Exporter` -> `Messaging Dispatcher`.
    - *Sub-Nodes*: `Dynamic Model Router`, `Blackboard Hub`, `Subprocess / Shell Runner`.
    - *Highlights*: Automated daily maintenance pipeline featuring a Human-in-the-Loop decision gate before applying patches, saving audit sign-offs to `docs/maintenance_audit_signoff.md` and broadcasting final status to Telegram.
- **Real Graph Execution Engine (`graph_executor.py`)**:
  - Live stateful pipeline runner executing node-by-node workflows via `POST /api/workflow/run`.
  - Dispatches real HTTP requests to external APIs and captures live telemetry.
  - Generates physical deliverable files directly into the `docs/` workspace directory.
  - Seamlessly triggers browser file downloads upon pipeline completion.
  - Dispatches live notifications to Telegram Bot chats via configured chat IDs.
- **Activity Palette & Canvas Icon Fidelity**:
  - 15+ specialized activities across Triggers, Orchestration, Agents, Governance, Tools, and Delivery.
  - Exact Activity Catalog icon and color resolution, ensuring dragged nodes retain their authentic visual branding on the canvas.
- **Freeform Canvas Panning & Precision Navigation**:
  - Drag and pan the canvas background freely with the mouse (`cursor-grab` / `cursor-grabbing`) to navigate large multi-agent DAGs.
  - Granular zoom scaling from 50% to 180% with synchronized dot-matrix grid movements.
  - Instant one-click **Reset View (100%)** button to recenter the canvas.
- **Per-Agent Workspace Context Binding**:
  - Each agent node displays a dedicated workspace badge (`📁 ws: <name>`) directly on its canvas card.
  - Granular selection via the **Activity & Agent Properties Drawer**: configure individual specialists to operate within specific workspaces.
- **Dual Execution Engine (Real Live Engine vs Local Step Sim)**:
  - **Live Engine (Real)**: Directly triggers backend execution via `POST /api/workflow/run` and updates active nodes with animated signal waves and status indicators.
  - **Step Sim Mode**: Deterministic local simulation mode to test and demonstrate pipeline topologies without GPU inference load.
- **JSON Schema Workflow Export**:
  - Export complete workflow configurations with nodes, lanes, edges, and configurations into standardized `locallm-agent-workflow.json` files for version control and sharing.
- **Calm, High-Contrast Theming (Dark & Light Mode)**:
  - Glare-free light theme built with soft slate surfaces (`#f1f5f9`), bold text contrast (`text-slate-900`/`text-slate-700`), and balanced grid dots.
  - Explicitly styled dark mode select menus and options ensuring zero text wash-out across all browsers and operating systems.


### 💻 Agentic Coding & Surgical Code Patching (Open Code Cockpit)
- **Surgical File Patching (`patch_file`)**:
  - Performs targeted search-and-replace block edits instead of full-file rewrites.
  - Prevents model hallucination, truncations, and accidental code destruction in large files.
  - Emits clear unified line diff previews before applying changes.
- **Built-in AST & Syntax Verification Guard (`check_syntax`)**:
  - Automatically verifies syntax before and after code modifications across Python (via standard library AST), JavaScript, TypeScript, JSON, HTML, and CSS.
  - Pinpoints line numbers and syntax error messages to immediately alert the agent to fix malformed code before committing.
- **Interactive `@` File Auto-Completion**:
  - Integrated into the interactive CLI prompt via `prompt_toolkit`.
  - Typing `@` displays a dynamic auto-completion popup listing project files across workspace and repository directories, allowing instant file injection into prompts.
- **Terminal Open Code Experience**:
  - Combines full conversational interaction with hands-on tool execution. Read files, edit lines surgically, check AST syntax, run tests via `execute_command`, and verify results directly from the terminal prompt.

### 📚 Local Knowledge Base & Zero-Dependency Agentic RAG Engine
- **Zero External Dependencies**:
  - No bloated vector databases or heavy external embedding frameworks required.
  - Powered by pure-Python BM25Okapi ranking (`bm25.py`) with term-frequency saturation, document length normalization, and token cleaning.
- **Structural Markdown Chunker (`chunker.py`)**:
  - Intelligent heading-aware document splitting respecting `#`, `##`, `###`, and `####` structural hierarchies.
  - Protects code blocks (```` ``` ````) and Markdown tables from being sliced mid-structure.
  - Configurable chunk size (default 600 words) with sliding overlap (100 words).
- **Isolated SQLite Storage Engine (`store.py`)**:
  - High-performance, embedded SQLite storage per workspace (`knowledge_index.db`).
  - Stores document metadata, chunk text, token counts, headings, and schema migrations.
- **Progressive Disclosure Strategy**:
  - Injects a compact topic catalog (~150 tokens) into system prompt instructions, alerting the model to available knowledge topics without consuming precious context tokens.
  - When specific questions arise, the model uses `search_knowledge` to retrieve only the most relevant passages on demand, preserving 95% of the LLM context window.
- **Native Knowledge Tools**:
  - `search_knowledge(query, top_k)`: Ranked retrieval with BM25Okapi relevance scores and chunk headings.
  - `index_knowledge(directory, file_patterns)`: Scans and indexes workspace docs, runbooks, and API specs into SQLite.

### 🤖 Unified Autonomous Coding Agent & Interactive Assistant
- **Consolidated Coding Agent Cockpit**: Interactive assistant (`locallm chat` and `locallm agent`) combines full conversational memory with multi-step autonomous execution (`MAX_TOOL_STEPS = 25`).
- **Autonomous Agent in Main Menu**: Directly accessible from the main interactive console menu or via `locallm agent` for dedicated multi-step goals.
- **Smart Task Termination & Early Exit Logic**: Evaluates multi-step execution on each turn and stops early when the user's objective is completed, preventing wasteful tool loops from spinning needlessly through the maximum iteration limit.
- **Hybrid Chat & Agent Mode**: In Assistant Chat, models seamlessly transition into autonomous action when given actionable tasks (such as inspecting code, auditing targets, or running commands) without conversational stalling or asking repetitive clarification questions.
- **Strict Workspace Sandboxing & Confinement**: All tools (`list_directory`, `read_file`, `write_file`, `patch_file`, `check_syntax`, `execute_command`, `get_current_directory`) are strictly locked into the active workspace directory (`~/.locallm/workspaces/<workspace_name>/`). Resolving `.` or relative paths always maps inside the workspace, preventing accidental leakage of host user files (`~`).
- **Anti-Loop Circuit Breaker**: Proactively halts repetitive identical tool invocations (if the exact same call is repeated twice consecutively), preventing infinite token-draining loops.
- **Focused Tool Sampling Temperature (`0.2`)**: Employs deterministic low-temperature sampling during tool turns to avoid conversational drift or hallucinations.
- **Direct Execution Authority**: The agent autonomously scaffolds directories, creates and refactors files, executes shell commands, inspects project repositories, and queries web documentation.
- **Granular Permission Policies**: Configured globally in `Settings -> Agent Permission Policy`:
  - `always_allow`: Fully hands-free autonomous coding and terminal execution.
  - `ask`: Interactive approval prompt (`Allow Once`, `Always Allow`, `Deny`) before mutating actions.
  - `deny`: Read-only execution mode blocking all filesystem modifications and shell execution.
- **Telegram Bot (`locallm telegram`)**: 24/7 bot daemon with per-user conversation memory, user ID whitelisting, Markdown-to-HTML formatting, and photo/document delivery tools.
- **WhatsApp Bot (`locallm whatsapp`)**: Terminal QR code pairing via Baileys bridge, multi-user memory, phone whitelist, group chat support, and automatic 15-digit LID resolution.
- **Cross-Channel Parity**: Uniform context telemetry (`• Context: 2,681/8,192 (32.7%) • Speed: 37.8 tok/s`) and slash commands (`/stats`, `/model`, `/clear`, `/sessions`, `/help`, `/multi`) across CLI, Telegram, and WhatsApp.

### 🧠 Dual-Tier Long-Term Memory System (Global & Workspace-Scoped)
- **Tier 1: Cross-Workspace Global User Memory (`~/.locallm/global_memory.json`)**:
  - Persists overarching user profile, communication rules, persona directives, and durable facts across all workspaces.
  - Autonomous memory maintenance tool (`update_user_memory`) enables the assistant to save, update, or remove preferences when instructed.
  - Injected automatically into system instructions across CLI, Web UI, Telegram, and WhatsApp (`[Global User Memory & Profile]`).
  - Strict security guard: sanitizes API keys, secrets, passwords, and raw Chain-of-Thought `<think>` tokens prior to saving.
- **Tier 2: Workspace-Scoped Auto-Memory (`~/.locallm/workspaces/<name>/memory.json`)**:
  - Completely isolated episodic project memory. Facts learned in Project A never leak into Project B.
  - **Zero-Friction Post-Turn Extraction**: Dispatches a lightweight background worker after conversation turns to automatically extract durable project facts (timelines, dates, inventory purchases, architectural decisions, and configurations).
  - **Smart Relevance Filter**: Automatically filters out casual chit-chat, trivial greetings, and transient debug noise.
  - **Bounded Memory Quota (Max 30 Facts)**: Preserves KV-cache budget and GPU VRAM headroom by maintaining only the most recent 30 facts with timestamps.
  - **Granular Workspace Toggle**: Easily enable or disable auto-extraction per workspace in the Web UI Workspace Modal or via `workspace.json` (`"auto_memory": true/false`).
  - **Context Grounding**: Injected dynamically into prompt context (`[Workspace Long-Term Memory & Project Context]`), enabling the model to remember facts across new sessions without re-explaining context.
  - **Memory Lifecycle & Session Pruning**: Keeps project memory clean and organized, pruning obsolete or session-specific facts upon chat session deletion.

### 🧠 Workspace Persona Engine (`AGENTS.md`) & Proactive Research
- **Customizable Persona Directives**: Every workspace contains its own `AGENTS.md` file defining how the model thinks, responds, and uses tools.
- **Auto-Scaffolding**: Newly created workspaces automatically inherit a production-grade persona template with zero manual configuration.
- **Decoupled Backend Prompts**: Core Python scripts remain clean and minimal; all system prompts and directives live directly in editable markdown.
- **Proactive Web Research**: Local models are instructed to never claim ignorance or lack of real-time data for unfamiliar entities, protocols, or products.
- **Turn 1 Refusal Interceptor**: If a model hesitates or admits a lack of knowledge on turn 1 (e.g. for niche enterprise tools), `locaLLM` automatically intercepts and nudges the model to execute `search_web` before synthesizing the final answer.

### 🛠️ Modular Tool Registry & Silent Tool Execution
- **Modular Tool Architecture (`locallm/core/tools/`)**: Tools are decoupled into domain packages (`filesystem.py`, `web.py`, `system.py`, `messaging.py`, `ui.py`, `memory.py`) and dynamically registered via `@tool` decorators.
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

### 🔄 Multi-Platform Inference Engine & Instant VRAM Management
- **Seamless Local & Cloud Hybrid Inference**: Effortlessly switch between local Ollama and external OpenAI-compatible backends (such as vLLM, LocalAI, iForte-GPU, or text-generation-webui) without data silos.
- **Instant VRAM Ejection on Platform Switch**: When switching active execution from Ollama to a remote platform, `locaLLM` immediately signals Ollama to unload models from GPU memory (`keep_alive: 0`), releasing local VRAM and system RAM instantly.
- **Direct Streaming Proxy Bridge**: The frontend bridge streams inference requests directly from the configured remote platform endpoint using saved Bearer authorization tokens, bypassing local model fallbacks and eliminating mismatched responses.
- **Fail-Safe Concrete Model Resolution**: Requests utilizing `'auto'` routing are dynamically resolved to valid default or installed models across both Ollama and custom platforms, preventing runtime `"model 'auto' not found"` errors.

### 🌐 Model Context Protocol (MCP) Multi-Server Support
- **Multi-Connection Architecture**: Connect to multiple MCP servers concurrently (`filesystem`, `github`, `postgres`, `sqlite`, remote APIs).
- **Transport Flexibility**: Native support for **`stdio`** (subprocesses via `npx`, `python`, `node`, `uvx`) and **`sse`** (remote HTTP/SSE streams).
- **Zero External Bloat**: High-performance, zero-conflict JSON-RPC 2.0 client built directly on standard Python libraries and HTTPX.
- **Cross-Platform & Standard Compatible**: Standard `mcp_servers.json` configuration compatible with standard MCP clients and Cursor.
- **Unified Tool Dispatch & Namespacing**: Discovered MCP tools are dynamically exposed to Chat, Autonomous ReAct Agent, Telegram Bot, and WhatsApp Bot with collision-free namespacing (`mcp__<server>__<tool>`).
- **Access Control & Privilege Gating**: Flag servers or individual tools as `privileged` to restrict them to authorized administrator callers only.
- **Interactive TUI & CLI**: Manage servers with `locallm mcp list`, `locallm mcp test <name>`, `locallm mcp enable/disable <name>`, or the interactive wizard in `Integrations -> Model Context Protocol (MCP)`.

### 🗂️ Zero-Bleed Workspaces, Skills & Isolated Sessions
- **Strict Context Isolation**: Each project workspace (`~/.locallm/workspaces/<name>/`) contains isolated `knowledge/`, `skills/`, `sessions/`, and `memory.json`. No cross-contamination across projects.
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
  ├── Assistant             -> Interactive chat & Open Code coding assistant with surgical patching, @ auto-complete, & typing effect
  ├── Autonomous Agent      -> Autonomous agent execution (Single ReAct Agent or Multi-Agent Team)
  │     ├── Single ReAct Agent      -> Single-model ReAct loop for sequential goals
  │     ├── Multi-Agent Team (Multi) -> Hierarchical team (Supervisor, Coder, Researcher, Auditor) with shared blackboard
  │     └── Back                    -> Return to Main Menu
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
| `locallm chat` | Launch interactive Open Code assistant session with surgical patching and `@` file auto-completion | `locallm chat --model auto` |
| `locallm agent` | Launch interactive coding agent (Single ReAct or Multi-Agent Team selector) | `locallm agent` / `locallm agent --task "Scaffold FastAPI app"` |
| `locallm agent --multi` | Launch hierarchical multi-agent team (Supervisor, Coder, Researcher, Auditor) | `locallm agent --multi --task "Build and audit test suite"` |
| `locallm serve` | Start OpenAI & n8n compatible HTTP API Gateway server (`/v1/chat/completions`) | `locallm serve --port 8080 --host 0.0.0.0` |
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

### 🌐 External Platform & n8n Integration Guide

`locaLLM` seamlessly integrates with external automation platforms such as **n8n**, **Flowise**, **LangChain**, and custom microservices. Two integration patterns are supported:

#### Pattern 1: Synchronous 1-Click Drop-in via OpenAI Node

Any platform with an OpenAI chat completion node can trigger full multi-agent coordination simply by specifying `model: "agent:multi"` or `model: "agent:auto"`:

```bash
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agent:multi",
    "messages": [
      {
        "role": "user",
        "content": "Audit all endpoints in api_server.py and verify syntax"
      }
    ]
  }'
```

In **n8n**:
1. Add an **OpenAI** node (or standard **HTTP Request** node).
2. Set **Base URL** to `http://127.0.0.1:8080/v1`.
3. Set **Model** to `agent:multi`.
4. Send your user prompt. The multi-agent coordinator (Supervisor, Coder, Researcher, Auditor) will execute the task and return the final aggregated response.

#### Pattern 2: Asynchronous Task Execution with Webhook Callbacks

For long-running engineering tasks, scripts, or distributed workflows, use the dedicated `/api/agent/run` endpoint:

**Trigger Async Task with Webhook Callback:**
```bash
curl -X POST http://127.0.0.1:8080/api/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Refactor database migrations and write unit tests",
    "workspace": "web_pentest",
    "async": true,
    "webhook_url": "https://n8n.example.com/webhook/locallm-finished"
  }'
```

**Immediate Response (HTTP 202 Accepted):**
```json
{
  "task_id": "task_9f81a7b2c0",
  "status": "queued",
  "workspace": "web_pentest",
  "webhook_configured": true
}
```

**Query Execution Status Manually (`GET /api/agent/status`):**
```bash
curl http://127.0.0.1:8080/api/agent/status?task_id=task_9f81a7b2c0
```

**Webhook Callback Payload Sent to n8n:**
When execution concludes, `locaLLM` automatically dispatches an HTTP POST payload to your configured webhook URL:
```json
{
  "task_id": "task_9f81a7b2c0",
  "status": "completed",
  "data": {
    "status": "completed",
    "goal": "Refactor database migrations and write unit tests",
    "output": "Successfully refactored migrations and verified all test suites.",
    "modified_files": ["migrations/002_add_roles.sql", "tests/test_migrations.py"],
    "steps": 6,
    "total_duration_seconds": 14.8
  }
}
```

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
| `/multi [task]` | `/team`, `multi-agent`, `team` | Dispatches task to hierarchical multi-agent coordination team (Supervisor, Coder, Researcher, Auditor). |
| `@<filename>` | `@file` | Real-time project file auto-completion powered by prompt_toolkit to inject file paths or content directly into context. |
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
4. **Project Repository Rules**: Loaded automatically from `<cwd>/AGENTS.md` (or other standard repository rule files) under `[Project Architecture & Rules]`.

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
| `patch_file` | Surgical code patcher | Replaces targeted code blocks via search-and-replace blocks without overwriting full files. Emits unified diff previews. |
| `check_syntax` | AST & syntax verification guard | Validates syntax for Python (AST), JavaScript, TypeScript, JSON, HTML, and CSS before and after edits. |
| `write_file` | Writes or overwrites files | Auto-creates parent directories; outputs written character count. |
| `read_file` | Reads file contents | UTF-8 safe with line numbers and token budget guards. |
| `list_directory` | Lists directory contents | Folder-first listing (`[DIR]` before `[FILE]`); expands aliases (`~`, `downloads`, `desktop`). |
| `create_directory` | Creates directories recursively | Scaffolds parent directories automatically anywhere on the filesystem. |
| `execute_command` | Executes shell commands | Adheres strictly to permission policy (`ask`, `always_allow`, `deny`). |
| `search_knowledge` | Agentic RAG search | Ranked BM25Okapi search across indexed workspace markdown docs and project specifications. |
| `index_knowledge` | Knowledge base indexer | Parses, chunks, and indexes workspace documentation into SQLite (`knowledge_index.db`). |
| `dispatch_agent_team` | Multi-agent team dispatcher | Decomposes tasks and delegates work to specialist agents with shared blackboard tracking. |
| `search_web` | Searches the web | Multi-engine support (`auto`, `duckduckgo`, `bing`, `custom`) to prevent network blocking. |
| `fetch_web` | Fetches webpage text | Markdown converter; direct raw `README.md` download for GitHub URLs. |
| `get_weather` | Real-time weather reporting | Plain-text weather via wttr.in with Windows console charmap safety. |
| `get_current_time` | System clock | Formatted local time, day, and date. |
| `update_user_memory` | Global memory manager | Stores and updates persistent user profile, communication rules, or facts across workspaces. |
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

### Workspace Configuration (`workspace.json`)
Each workspace maintains its metadata, persona overrides, and feature toggles in `~/.locallm/workspaces/<name>/workspace.json`:

```json
{
  "name": "default",
  "description": "Default development workspace",
  "instructions": "",
  "icon": "folder",
  "icon_color": "#0ea5e9",
  "auto_memory": true
}
```

### Long-Term Memory Storage Files
- **Global User Memory**: `~/.locallm/global_memory.json` (stores cross-workspace user persona, communication preferences, and persistent facts).
- **Workspace Memory**: `~/.locallm/workspaces/<name>/memory.json` (stores up to 30 auto-extracted episodic project facts with timestamps, strictly isolated per workspace).

---

## 🧪 Testing & Verification

Run the test suites to verify backend functionality, multi-agent graph orchestration, and frontend end-to-end flows:

```bash
# 1. Run all Python unit and integration tests (250+ test suites)
uv run pytest -q

# 2. Run Playwright End-to-End Workflow Studio Automation Test
uv run python scripts/verify_workflow_playwright.py

# 3. Standard library unit tests discovery fallback
python -m unittest discover -s tests -p "test_*.py"
```

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
