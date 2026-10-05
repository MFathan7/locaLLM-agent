# LocaLLM Web Cockpit

> **Modern Apple Liquid Glass Web Interface for locaLLM, featuring 1:1 real-time CLI synchronization, dual-theme support, rich Markdown parsing, and autonomous agent controls.**

Built with **React 19**, **TypeScript**, **Tailwind CSS v4**, and **Motion (`motion/react`)**.

---

## 🌟 Key Features

### 🔮 Liquid Glass Materiality
- **Curved Specular Highlights**: Multi-layered frosted glass panels (`backdrop-filter: blur(24px)`) with realistic rim lighting, subtle inner refraction, and glass sheen.
- **Aurora Mesh Background**: Blurred gradient backdrop that gently animates during empty chats and transitions seamlessly when conversations begin.
- **Spring Physics Layout**: Fluid, physics-based transitions when opening menus, switching workspaces, or resizing the navigation sidebar.

### ⚡ 1:1 Live CLI Synchronization
- **Single Source of Truth**: Reads from and writes directly to `~/.locallm/config.json` and `~/.locallm/workspaces/`.
- **Zero Data Silos**: Changing temperature, default models, agent policies, or active platforms in the Web UI immediately updates the CLI configuration, and vice versa.
- **Unified Workspace Sessions**: Access the exact same chat sessions, agent personas (`AGENTS.md`), knowledge docs, and skills whether working in the terminal or browser.

### 🌗 High-Contrast Dual-Theme Design
- **Sleek Dark Mode**: Deep obsidian and zinc surfaces (`#070a12`) with frosted translucent cards.
- **Crisp Light Mode**: Soft glare-free background with bold, high-contrast dark typography (`text-slate-950 font-bold`) ensuring complete legibility without washed-out gray text.

### 📝 Rich Markdown, Tables & Code Highlighting
- **Clean Reasoning & Trace Filtering**: Automatically hides `<think>...</think>` reasoning tokens and intermediate tool executions from the final response, with a live `Thinking and reasoning...` badge during inference.
- **Refined Tables with Hover Copy Button**: Clean horizontal-only grid lines (no vertical lines) with centered, bold column headers and no outer borders. Hovering reveals a copy icon beside the table that copies the whole table with headers in Markdown and HTML.
- **Collapsible Sources Side Panel**: External references and search results are parsed into domain-branded cards with favicons, viewable in a sliding side panel.
- **One-Click Word Export (`.doc`)**: Export any assistant response directly to a styled Microsoft Word document.
- **Code Blocks & Lightbox**: Multi-language syntax-highlighted code blocks with copy buttons, and full-resolution inline image zoom modal.

### 🎯 Conversation Workflow & Polish
- **Tactile Copy Buttons**: Copy buttons with hover tooltips on both assistant responses and user message bubbles.
- **Lazy "New Chat" Creation**: Clicking New Chat switches to a clean draft mode without creating empty session files on disk until the first message is sent.
- **Intelligent Auto Chat Title**:
  - Instant heuristic title extraction stripping conversational filler words (*"tolong buatkan"*, *"can you help me"*, etc.).
  - Asynchronous background AI title synthesis naming conversations by user goal without slowing down inference.
- **Adaptive Header Navigation**: Navbar search icon is hidden when the sidebar is expanded and appears when collapsed, with zero gap during spring transitions.

### 🔍 Zero-Latency Conversation Search
- **Instant Search Overlay**: Activated via header search button or universal keyboard shortcuts (`Ctrl+F` / `Cmd+K`).
- **Debounced Keystrokes (120ms)**: Zero typing lag even across extensive multi-megabyte chat archives.
- **Contextual Snippets**: Automatically extracts ~120 characters centered around the matched keywords instead of dumping entire messages.
- **Non-Blocking Navigation**: Instantly closes the overlay and transitions to the selected chat without freezing the browser thread.

### ⬇️ Centered Floating Scroll-to-Bottom Button
- Automatically detects scroll distance from bottom.
- Displays a minimalist, circular icon-only button centered at the bottom of the chat viewport (`left-1/2 -translate-x-1/2`).
- Vanishes automatically when scrolling back down near the latest message.

### 🎛️ Settings & Model Picker
- **Model Picker with Platform Subtitle**: Displays model name on top and platform name (*Ollama*, *OpenAI*, or custom platforms) underneath.
- **Dynamic Platform Switcher**: Switch between native local Ollama and custom OpenAI-compatible platforms (e.g. vLLM, LocalAI).
- **Dynamic Model Dropdown**: Automatically re-queries available models on the active platform with a 60-second in-memory cache and connection timeout guards.
- **Inference & Policy Controls**: Adjust sampling temperature, context window limits, system prompts, agent autonomy policies (`ask`, `always_allow`, `deny`), and OpenAI gateway settings.

### ➕ Dynamic Chat Input, Attachments & Starters
- **Multi-File Attachments (up to 5 files)**: Drag-and-drop or upload images, PDFs, Word documents (`.docx`), and text/code files directly into the prompt context with interactive preview chips.
- **Multi-Turn Document Context Retention**: File content is automatically maintained across subsequent conversation turns so the model retains full document awareness during follow-up questions.
- **Interactive Starter Prompts**: 3 randomized starter suggestion cards on empty sessions to jumpstart coding, debugging, or brainstorming tasks in one click.
- **Dynamic Web Chat Greetings**: Randomized modern AI greetings (ChatGPT/Claude style) that refresh on every new chat.
- **AI Disclaimer Header**: Subtle, sleek disclaimer header above the chat input box (*"LocaLLM can stumble sometimes. Stay sharp and double-check key info."*).
- **Web Search & Agent Tool Toggles**: Direct toggle buttons to enable or disable autonomous tools or real-time web research on a per-prompt basis.

---

## 🚀 Getting Started

### 1. Prerequisites
- **Node.js**: v18.0.0 or higher
- **npm**: v9.0.0 or higher
- **locaLLM core**: Installed in parent directory (with Ollama or an OpenAI-compatible service running)

### 2. Development Mode

To start the Vite development server with the built-in local backend bridge:

```bash
# Navigate to frontend folder
cd frontend

# Install dependencies (first run only)
npm install

# Start development server
npm run dev
```

Open your browser at:
```text
http://localhost:5173
```

### 3. Production Build

To validate TypeScript types and generate an optimized static bundle:

```bash
npm run build
```

The production output is generated in `dist/`.

To preview the production build locally:

```bash
npm run preview
```

---

## 📁 Project Structure

```text
frontend/
├── src/
│   ├── components/
│   │   ├── AuroraBackground.tsx   # Ambient blurred gradient backdrop
│   │   ├── ChatContainer.tsx      # Chat stream, bubble cards & centered scroll button
│   │   ├── ChatInput.tsx          # Dynamic message input bar & spring positioning
│   │   ├── EmptyState.tsx         # Workspace greeting & quick starter actions
│   │   ├── MarkdownRenderer.tsx   # Markdown parser, code copy & image lightbox
│   │   ├── ModelPicker.tsx        # Dynamic model selector dropdown
│   │   ├── PlusMenu.tsx           # File upload, web search & tools toggles
│   │   ├── SearchOverlay.tsx      # Debounced snippet-based conversation search
│   │   ├── SettingsModal.tsx      # High-contrast settings cockpit & platform manager
│   │   ├── Sidebar.tsx            # Workspace selector, session history & collapse toggle
│   │   └── ThemeToggle.tsx        # Dark/Light mode theme switch button
│   ├── hooks/
│   │   └── useLocaLLM.ts          # Core state hook managing sessions, config & sync
│   ├── services/
│   │   └── api.ts                 # API client for backend bridge communication
│   ├── types/
│   │   └── index.ts               # Shared TypeScript interfaces & types
│   ├── App.tsx                    # Top-level application shell and layout
│   ├── main.tsx                   # React root entrypoint
│   └── index.css                  # Tailwind v4 directives & Liquid Glass CSS tokens
├── vite.config.ts                 # Vite config with built-in locaLLM IPC/API middleware
├── package.json                   # Dependencies & scripts
└── tsconfig.json                  # TypeScript configuration
```

---

## 🔌 API Bridge Architecture

The development server (`vite.config.ts`) includes a zero-dependency local bridge plugin that exposes REST endpoints directly to the filesystem and local services:

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/config` | `GET`, `POST` | Reads and updates `~/.locallm/config.json`. |
| `/api/workspaces` | `GET`, `POST` | Lists and creates isolated project workspaces. |
| `/api/sessions` | `GET`, `POST`, `DELETE` | Manages conversation histories in active workspace. |
| `/api/models` | `GET` | Queries live models from Ollama (`/api/tags`) or custom platforms (`/models`). |
| `/api/chat` | `POST` | Streams assistant tokens using Ollama or OpenAI-compatible backend. |

---

## 📄 License

This frontend is part of the `locaLLM` platform and is licensed under the MIT License.
