# locaLLM Workspace Rules for Antigravity AI Assistant

Developer guidelines and operational standards for building and extending the locaLLM project within this workspace.

---

## Core Operational Rules (Derived from User Reviews):

1. **Console UI & Menu Labels**:
   - DO NOT use icons or emojis in Questionary menu labels (`choices=[]`). Labels must be pure text.
   - Keep menu labels concise and clean (e.g., `Telegram`, not `Telegram Bot Runner (24/7 Daemon)`).
   - Never use dim/dark purple text (`[dim]`) on Windows consoles; use high-contrast light gray (`#bbbbbb` or `#aaaaaa`).
   - Use the Square Snake Spinner (`▘▀▝▐▗▄▖▌`) during model thinking and tool execution.

2. **Menu Architecture & Domain Segregation**:
   - `Services` Menu: Controls background inference daemons per platform (`Ollama`, `LM Studio`). Never auto-spawn server processes silently without explicit user invocation.
   - `Integrations` Menu:
     - Submenu `Telegram`: `Start Bot Runner`, `Configure Bot Token`, `Configure Allowed Users Whitelist`, `Back`.
     - Submenu `Agent & Automation`: `Run Agent Task`, `Auto-Approve Shell Commands`, `Back`.
   - `Settings` Menu: Reserved strictly for core model inference parameters (`Active Backend`, `Sampling Temperature`, `Context Window Limit`, `System Prompt`).
   - Every submenu must include a `Back` choice.
   - Always prompt with a pause (`Press Enter to return...`) after terminal output before returning to menus so `console.clear()` does not flash away information.

3. **Interactive Assistant Session**:
   - Silent Tool Execution: Tools must run quietly behind the thinking spinner without dumping raw logs into the chat window.
   - Context Usage Telemetry: Display cumulative session token usage against the model context limit (`• Context: 2,681/8,192 tokens (32.7%) • Speed: 37.8 tok/s`), never per-turn response counts.
   - No redundant welcome banners at chat start (the header already displays this). Show only a brief light gray command hint.
   - Double Fallback: If streaming returns 0 tokens, immediately trigger a non-streaming fallback turn so the assistant never silently terminates after thinking.

4. **Tools & Filesystem Intelligence**:
   - Always use `resolve_smart_path` to handle user directory aliases (`downloads`, `desktop`, `documents`, `~`).
   - `list_directory` must prioritize subdirectories (`[DIR]`) at the top of the output before files.
   - Provide `fetch_web` with direct raw README fetching for GitHub links.
   - System prompts must enforce tool execution authority and forbid "I am just an AI" refusals. Prompts must be modular to cleanly accommodate future Skills and Knowledge (RAG) expansions.

5. **Hardware Sizing**:
   - VRAM Compatibility Formula: $\text{Model Size (GB)} + 2.0\text{ GB}$.
   - Mark as `FIT` if within Free VRAM, or `OFFLOAD (CPU/RAM)` if it exceeds available GPU VRAM.

6. **Test Verification**:
   - Always run the test suite after modifications: `python -m unittest discover -s tests -p "test_*.py"`.

7. **Strict English-Only in Codebase**:
   - All source code, docstrings, comments, variable names, UI text, Questionary menu choices, CLI help guides, error messages, test fixtures, and bot responses must strictly be written in English.
   - Never use Indonesian or mixed-language strings in any script or user-facing interface.

8. **Cross-Platform Uniformity & Context Telemetry**:
   - Multi-platform feature parity across Assistant CLI, Telegram Bot, and WhatsApp Bot.
   - Real-time cumulative context telemetry tracking and logging (`• Context: X/Y tokens (Z%) • Speed: S tok/s`).
   - Universal command parity (`/stats`, `/model`, `/clear`, `/reset`, `/help`) on all platforms.
   - Silent tool execution behind native loading indicators without polluting chat history.



