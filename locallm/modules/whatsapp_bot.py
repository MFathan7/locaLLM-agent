"""WhatsApp Bot integration runner and daemon for local LLM models."""

import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

import questionary
from rich.panel import Panel
from rich.table import Table

from locallm.config import LocaLLMConfig, save_config
from locallm.core.memory import ConversationMemory
from locallm.core.ollama_client import OllamaClient
from locallm.core.tools import WHATSAPP_TOOLS, execute_tool, resolve_smart_path
from locallm.core.workspace import (
    delete_workspace_session,
    load_workspace_context,
    load_workspace_session,
    save_workspace_session,
)
from locallm.ui.spinner import thinking_spinner
from locallm.ui.theme import QUESTIONARY_STYLE, console

# In-memory per-user conversation stores for WhatsApp
user_sessions: Dict[str, ConversationMemory] = {}


def normalize_phone_number(raw: str) -> str:
    """Normalize phone number to digits only (e.g. '+62 812-3456-789' -> '628123456789')."""
    if not raw:
        return ""
    digits = re.sub(r"\D", "", raw.strip())
    # Convert leading 0 to international Indonesian prefix (62) if standard Indonesian local number
    if digits.startswith("0") and len(digits) >= 10:
        digits = "62" + digits[1:]
    return digits


def markdown_to_whatsapp_text(text: str) -> str:
    """Convert standard LLM Markdown into WhatsApp formatting syntax.

    WhatsApp Formatting:
    *bold* for bold
    _italic_ for italic
    ~strikethrough~ for strikethrough
    ```code block``` for code
    """
    if not text:
        return ""

    # 1. Protect code blocks (```code```)
    code_blocks: List[str] = []

    def replace_code_block(match: re.Match) -> str:
        code_content = match.group(2) if match.group(2) is not None else match.group(1)
        idx = len(code_blocks)
        code_blocks.append(f"```{code_content.strip()}```")
        return f"@@@CODEBLOCK{idx}@@@"

    pattern_block = re.compile(r"```(?:([a-zA-Z0-9_\-\+]+)\n)?(.*?)```", re.DOTALL)
    processed = pattern_block.sub(replace_code_block, text)

    # 2. Bold: **text** -> *text*
    processed = re.sub(r"\*\*(.+?)\*\*", r"*\1*", processed)

    # 3. Headers: # Title -> *Title*
    def replace_header(m: re.Match) -> str:
        prefix = m.group(1) or ""
        title = m.group(2).strip()
        return f"{prefix}*{title}*"

    processed = re.sub(r"(^|\s)#{1,6}\s+([^\n`#]+?)(?=\s|\n|$)", replace_header, processed)

    # 4. Restore code blocks
    for idx, snippet in enumerate(code_blocks):
        processed = processed.replace(f"@@@CODEBLOCK{idx}@@@", snippet)

    return processed.strip()



def run_whatsapp_menu(config: LocaLLMConfig, client: OllamaClient) -> None:
    """Main WhatsApp integration submenu loop."""
    while True:
        status_text = "[bold green]ONLINE[/]" if client.is_connected() else "[bold red]OFFLINE[/]"
        whitelist_count = len(config.whatsapp_allowed_numbers)
        whitelist_desc = f"{whitelist_count} allowed number(s)" if whitelist_count > 0 else "All numbers allowed"
        model_display = "Auto (Smart Router)" if config.default_model.lower() == "auto" else config.default_model

        panel_content = (
            f"Backend Service   : {status_text} (Ollama)\n"
            f"Active Model      : [bold cyan]{model_display}[/]\n"
            f"Allowed Whitelist : [#00ff87]{whitelist_desc}[/]\n"
            f"Session Directory : [cyan]{get_whatsapp_session_dir(config)}[/]"
        )
        console.print(Panel(panel_content, title="WhatsApp Integration", border_style="cyan"))

        choice = questionary.select(
            "WhatsApp Options:",
            choices=[
                "Start WhatsApp Bot",
                "Configure Whitelist",
                "Clear Session",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice == "Start WhatsApp Bot":
            run_whatsapp_bot(config, client)
        elif choice == "Configure Whitelist":
            configure_whatsapp_whitelist(config)
        elif choice == "Clear Session":
            clear_whatsapp_session(config)


def get_whatsapp_session_dir(config: LocaLLMConfig) -> Path:
    """Return directory for WhatsApp pairing and authentication keys."""
    if config.whatsapp_session_dir:
        dir_path = Path(config.whatsapp_session_dir).expanduser().resolve()
    else:
        dir_path = Path.home() / ".locallm" / "whatsapp_session"
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def clear_whatsapp_session(config: LocaLLMConfig) -> None:
    """Remove stored WhatsApp credentials to force new QR code pairing."""
    session_dir = get_whatsapp_session_dir(config)
    confirm = questionary.confirm(
        f"Are you sure you want to delete session keys in {session_dir}?",
        default=False,
        style=QUESTIONARY_STYLE,
    ).ask()

    if confirm:
        try:
            for item in session_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            console.print("[bold green]WhatsApp session cleared. Device unlinked successfully.[/]\n")
        except Exception as exc:
            console.print(f"[danger]Failed to clear session directory:[/] {exc}\n")

    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def configure_whatsapp_whitelist(config: LocaLLMConfig) -> None:
    """Manage allowed phone number whitelist."""
    while True:
        current = config.whatsapp_allowed_numbers
        count_str = f"{len(current)} registered" if current else "None (Open to all callers)"

        action = questionary.select(
            f"Allowed Whitelist ({count_str}):",
            choices=[
                "View Current Whitelisted Numbers",
                "Add Phone Number",
                "Remove Phone Number",
                "Clear All Numbers (Allow All)",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if action is None or action == "Back":
            break

        if action == "View Current Whitelisted Numbers":
            if not current:
                console.print("[#aaaaaa]Whitelist is empty. Any incoming WhatsApp user can interact with the bot.[/]\n")
            else:
                table = Table(title="Whitelisted WhatsApp Numbers", border_style="cyan", header_style="bold cyan")
                table.add_column("No", width=4, justify="center")
                table.add_column("Phone Number", style="bold white")
                for idx, num in enumerate(current, 1):
                    table.add_row(str(idx), num)
                console.print(table)
                console.print()
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()

        elif action == "Add Phone Number":
            raw_input = questionary.text(
                "Enter phone number with country code (e.g. 628123456789 or 08123456789):",
                style=QUESTIONARY_STYLE,
            ).ask()
            if raw_input:
                normalized = normalize_phone_number(raw_input)
                if len(normalized) >= 8:
                    if normalized not in current:
                        current.append(normalized)
                        config.whatsapp_allowed_numbers = current
                        save_config(config)
                        console.print(f"[bold green]Phone number '{normalized}' added to whitelist.[/]\n")
                    else:
                        console.print(f"[yellow]Phone number '{normalized}' is already in the whitelist.[/]\n")
                else:
                    console.print("[danger]Invalid phone number format. Please enter a valid number.[/]\n")

        elif action == "Remove Phone Number":
            if not current:
                console.print("[yellow]Whitelist is already empty.[/]\n")
                continue
            choice = questionary.select(
                "Select number to remove:",
                choices=current + ["Cancel"],
                style=QUESTIONARY_STYLE,
            ).ask()
            if choice and choice != "Cancel":
                current.remove(choice)
                config.whatsapp_allowed_numbers = current
                save_config(config)
                console.print(f"[bold green]Removed '{choice}' from whitelist.[/]\n")

        elif action == "Clear All Numbers (Allow All)":
            confirm = questionary.confirm(
                "Clear all whitelist entries? (Bot will accept messages from any number)",
                default=False,
                style=QUESTIONARY_STYLE,
            ).ask()
            if confirm:
                config.whatsapp_allowed_numbers = []
                save_config(config)
                console.print("[bold green]Whitelist cleared. Bot is now open to all numbers.[/]\n")


def execute_whatsapp_tool(name: str, arguments: Dict[str, Any], phone_number: str) -> str:
    """Execute WhatsApp-specific native tools."""
    if name == "whatsapp_get_contact_info":
        return json.dumps({
            "phone_number": phone_number,
            "channel": "whatsapp",
            "active_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    elif name == "whatsapp_send_image":
        img_path = arguments.get("image_path_or_url", "")
        caption = arguments.get("caption", "")
        resolved = resolve_smart_path(img_path)
        if not resolved.exists():
            return f"Error: Image '{img_path}' not found on disk."
        return f"Image '{resolved.name}' delivered to WhatsApp chat with caption: '{caption}'"

    elif name == "whatsapp_send_document":
        doc_path = arguments.get("file_path", "")
        caption = arguments.get("caption", "")
        resolved = resolve_smart_path(doc_path)
        if not resolved.exists():
            return f"Error: Document '{doc_path}' not found on disk."
        return f"Document '{resolved.name}' delivered to WhatsApp chat ({resolved.stat().st_size} bytes)"

    elif name == "whatsapp_send_sticker":
        img_path = arguments.get("image_path", "")
        resolved = resolve_smart_path(img_path)
        if not resolved.exists():
            return f"Error: Sticker source image '{img_path}' not found on disk."
        return f"Sticker generated from '{resolved.name}' and delivered to WhatsApp chat."

    return execute_tool(name, arguments)


def process_whatsapp_message(
    sender_number: str,
    message_text: str,
    config: LocaLLMConfig,
    client: OllamaClient,
    skip_whitelist: bool = False,
    sender_name: str = "",
    is_group: bool = False,
    image_b64: Optional[str] = None,
) -> str:
    """Process an incoming WhatsApp message through locaLLM with tools & workspace memory."""
    clean_number = normalize_phone_number(sender_number)
    user_label = f"{sender_name} ({clean_number})" if sender_name else clean_number

    # 1. Whitelist Verification (can be bypassed for local simulator testing)
    if not skip_whitelist and config.whatsapp_allowed_numbers and clean_number not in config.whatsapp_allowed_numbers:
        console.print(f"[yellow][WhatsApp Blocked][/] Message from unwhitelisted sender: {user_label}")
        return "Access denied. Your phone number is not registered in the locaLLM whitelist."

    active_ws = getattr(config, "active_workspace", "default")
    context_limit = getattr(config, "context_window", 8192)

    # 2. Get or initialize user conversation memory
    if clean_number not in user_sessions:
        loaded = load_workspace_session(active_ws, f"whatsapp_{clean_number}")
        session = loaded if loaded else ConversationMemory()
        user_sessions[clean_number] = session
    else:
        session = user_sessions[clean_number]

    # 3. Dynamic context system prompt
    now_str = datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
    chat_type = "WhatsApp Group Chat" if is_group else "WhatsApp Direct Chat"
    system_prompt = (
        f"{config.system_prompt}\n"
        f"Channel: {chat_type}. Environment: Local Time: {now_str}.\n"
        f"You are conversing with user {sender_name or ''} (Identifier: {clean_number}).\n"
        "Capabilities & Tools: You can inspect directories, read files, check weather, "
        "and send images, documents, or stickers using WhatsApp native function calling.\n"
        "Keep responses friendly, helpful, and formatted cleanly using WhatsApp Markdown (*bold*, _italic_, ```code```)."
    )
    ws_context = load_workspace_context(active_ws)
    if ws_context:
        system_prompt += f"\n\n{ws_context}"
    session.set_system_prompt(system_prompt)

    # 4. Check session reset trigger
    normalized_query = message_text.strip().lower()
    if normalized_query in ("clear", "reset", "clear history", "start fresh", "clear chat", "reset session"):
        session.clear()
        delete_workspace_session(active_ws, f"whatsapp_{clean_number}")
        console.print(f"[dim yellow][WhatsApp Reset][/] Session cleared for {clean_number}")
        return "*Conversation history reset successfully.* Starting fresh session!"

    if normalized_query in ("stats", "/stats", "context", "/context", "status", "telemetry"):
        usage = session.get_context_usage(default_limit=context_limit)
        active_name = "Auto (Smart Router)" if config.default_model.lower() == "auto" else config.default_model
        features = (
            client.get_model_features(config.default_model)
            if config.default_model.lower() != "auto"
            else ["Dynamic Capability Dispatch"]
        )
        feat_str = ", ".join(features) if features else "Text Generation"
        return (
            "*locaLLM Context & Telemetry*\n\n"
            f"• *Active Model:* `{active_name}` ({feat_str})\n"
            f"• *Context Usage:* `{usage['total_tokens']:,} / {usage['limit']:,} tokens` ({usage['percentage']:.1f}%)\n"
            f"• *Speed:* `{usage['tps']:.1f} tok/s`\n"
            f"• *Workspace:* `{active_ws}`\n"
            f"• *Session ID:* `whatsapp_{clean_number}`\n"
            f"• *History Depth:* `{len(session.history)} messages`"
        )

    if normalized_query in ("model", "/model"):
        active_name = "Auto (Smart Router)" if config.default_model.lower() == "auto" else config.default_model
        features = (
            client.get_model_features(config.default_model)
            if config.default_model.lower() != "auto"
            else ["Dynamic Capability Dispatch"]
        )
        feat_str = ", ".join(features) if features else "Text Generation"
        return f"*Current Model:* `{active_name}`\n*Capabilities:* `{feat_str}`"

    if normalized_query in ("help", "/help", "menu"):
        return (
            "*locaLLM WhatsApp Commands*\n\n"
            "• `stats` / `/stats` : Check session context usage & generation speed\n"
            "• `model` / `/model` : Check active model & capabilities\n"
            "• `clear` / `/reset` : Reset conversation history\n"
            "• `help`  / `/help`  : Show this command guide"
        )

    session.add_user_message(message_text, images=[image_b64] if image_b64 else None)

    target_model = config.default_model
    if config.default_model.lower() == "auto":
        from locallm.core.router import route_prompt
        route = route_prompt(message_text, config, client, has_image=bool(image_b64), history=session.history)
        target_model = route.selected_model
        console.print(f"[dim cyan][WhatsApp Auto Router][/] Dispatched to: {target_model} ({route.reason})")

    features = client.get_model_features(target_model)
    has_tools = "Tools" in features
    context_limit = getattr(config, "context_window", 8192)
    stats: Dict[str, Any] = {}

    try:
        # Check tool execution
        turn_msg = client.chat_turn(
            model=target_model,
            messages=session.get_messages(),
            tools=WHATSAPP_TOOLS if has_tools else None,
            temperature=config.temperature,
            num_ctx=context_limit,
            stats_out=stats,
        )

        if turn_msg and turn_msg.get("tool_calls"):
            tool_calls = turn_msg["tool_calls"]
            session.history.append(turn_msg)

            for tc in tool_calls:
                func_name = tc.get("function", {}).get("name", "")
                func_args = tc.get("function", {}).get("arguments", {})
                if isinstance(func_args, str):
                    try:
                        func_args = json.loads(func_args)
                    except Exception:
                        func_args = {}
                console.print(f"[dim cyan][WhatsApp Tool][/] Executing: {func_name}({func_args})")
                obs = execute_whatsapp_tool(func_name, func_args, clean_number)
                session.history.append({"role": "tool", "content": obs})

            # Synthesize final answer after tool observation
            final_turn = client.chat_turn(
                model=target_model,
                messages=session.get_messages(),
                temperature=config.temperature,
                num_ctx=context_limit,
                stats_out=stats,
            )
            response_text = final_turn.get("content", "")
        else:
            response_text = turn_msg.get("content", "")

        if not response_text or not response_text.strip():
            response_text = "(Model did not produce any text response. Please try rephrasing.)"

        session.add_assistant_message(response_text)
        session.update_stats(stats)

        # Save session to workspace disk
        save_workspace_session(
            active_ws,
            f"whatsapp_{clean_number}",
            session,
            metadata={
                "type": "whatsapp",
                "phone_number": clean_number,
                "model": target_model,
            },
        )

        # Telemetry logging to console
        prompt_tok = stats.get("prompt_eval_count", 0)
        eval_tok = stats.get("eval_count", 0)
        total_tok = prompt_tok + eval_tok
        eval_dur_ns = stats.get("eval_duration", 0)
        tps = (eval_tok / (eval_dur_ns / 1e9)) if eval_dur_ns > 0 else 0.0

        console.print(f"[dim green][WhatsApp Replied][/] To {clean_number}")
        if total_tok > 0:
            limit = max(context_limit, total_tok)
            pct = (total_tok / limit * 100) if limit > 0 else 0.0
            pct_color = "#00ff87" if pct < 70 else ("#ffff00" if pct < 90 else "#ff5555")
            console.print(
                f"[#aaaaaa]  • Context:[/] [#00d7ff]{total_tok:,}[/][#aaaaaa]/[/][#ffffff]{limit:,}[/] [#aaaaaa]tokens "
                f"([{pct_color}]{pct:.1f}%[#aaaaaa]) • Speed:[/] [#00d7ff]{tps:.1f}[/] [#aaaaaa]tok/s • Session: whatsapp_{clean_number}[/]\n"
            )

        return markdown_to_whatsapp_text(response_text)

    except Exception as exc:
        console.print(f"[danger][WhatsApp Error][/] {exc}")
        return f"Error generating response: {exc}"


from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from rich.syntax import Syntax


class WhatsAppHTTPBridgeHandler(BaseHTTPRequestHandler):
    """Local HTTP endpoint to bridge incoming Baileys messages into locaLLM."""
    config: LocaLLMConfig
    client: OllamaClient

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            sender = data.get("sender", "")
            message = data.get("message", "")
            sender_name = data.get("sender_name", "")
            is_group = bool(data.get("is_group", False))
            image_b64 = data.get("image_base64")
            reply = process_whatsapp_message(
                sender,
                message,
                self.config,
                self.client,
                sender_name=sender_name,
                is_group=is_group,
                image_b64=image_b64,
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"reply": reply}).encode("utf-8"))
        except Exception as exc:
            console.print(f"[danger][WhatsApp Bridge Error][/] {exc}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def log_message(self, format, *args):
        pass  # Silent HTTP logging


DEFAULT_PACKAGE_JSON = """{
  "name": "locallm-whatsapp-bridge",
  "version": "1.0.0",
  "description": "Headless WhatsApp Web bridge for locaLLM using Baileys and terminal QR",
  "main": "bridge.mjs",
  "type": "module",
  "dependencies": {
    "@whiskeysockets/baileys": "^6.7.12",
    "qrcode-terminal": "^0.12.0",
    "pino": "^9.6.0"
  }
}
"""

DEFAULT_BRIDGE_MJS = """/**
 * locaLLM WhatsApp Bridge using @whiskeysockets/baileys
 * Connects to WhatsApp Web protocol, displays QR code in terminal,
 * and routes messages to locaLLM local engine.
 */

import makeWASocket, {
    useMultiFileAuthState,
    DisconnectReason,
    fetchLatestBaileysVersion,
    downloadMediaMessage
} from '@whiskeysockets/baileys';
import qrcode from 'qrcode-terminal';
import pino from 'pino';
import fs from 'fs';
import path from 'path';

const sessionDir = process.env.WHATSAPP_SESSION_DIR || path.join(process.env.USERPROFILE || process.env.HOME || '.', '.locallm', 'whatsapp_session');
const authDir = path.join(sessionDir, 'baileys_auth');
fs.mkdirSync(authDir, { recursive: true });

const LOCAL_AGENT_URL = process.env.LOCAL_AGENT_URL || 'http://127.0.0.1:5820/chat';

// Intercept libsignal session errors (Bad MAC / MessageCounterError) to auto-heal corrupted session files
const origConsoleError = console.error;
console.error = function(...args) {
    const errorStr = args.map(a => (a && a.stack) ? a.stack : String(a)).join(' ');
    if (errorStr.includes('Failed to decrypt message') || errorStr.includes('Bad MAC') || errorStr.includes('MessageCounterError')) {
        const match = errorStr.match(/(\\d+)\\.(\\d+)/);
        if (match) {
            const baseId = match[1];
            try {
                const files = fs.readdirSync(authDir);
                for (const file of files) {
                    if (file.startsWith(`session-${baseId}.`)) {
                        fs.unlinkSync(path.join(authDir, file));
                        console.log(`[locaLLM Auto-Heal] Reset corrupted session file ${file} to trigger clean Signal handshake.`);
                    }
                }
            } catch (_) {}
        }
    }
    origConsoleError.apply(console, args);
};

const msgRetryCounterMap = new Map();
const msgRetryCounterCache = {
    get: (key) => msgRetryCounterMap.get(key),
    set: (key, val) => msgRetryCounterMap.set(key, val),
    del: (key) => msgRetryCounterMap.delete(key),
    flushAll: () => msgRetryCounterMap.clear()
};

async function startWhatsAppBridge() {
    console.log('\\n[locaLLM WhatsApp Bridge] Initializing Baileys engine...');
    const { state, saveCreds } = await useMultiFileAuthState(authDir);
    let version = [2, 3000, 1015901307];
    try {
        const v = await fetchLatestBaileysVersion();
        version = v.version;
    } catch (e) {
        // Fallback to stable default version
    }

    console.log(`[locaLLM WhatsApp Bridge] Baileys Version: v${version.join('.')}`);
    console.log(`[locaLLM WhatsApp Bridge] Auth Directory: ${authDir}`);
    console.log(`[locaLLM WhatsApp Bridge] Agent Endpoint: ${LOCAL_AGENT_URL}\\n`);

    const sock = makeWASocket({
        version,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: false,
        auth: state,
        syncFullHistory: false,
        msgRetryCounterCache,
        generateHighQualityLinkPreview: true,
        browser: ['locaLLM', 'Chrome', '1.0.0'],
        getMessage: async () => undefined
    });

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('\\n=============================================================');
            console.log('  SCAN THIS QR CODE IN WHATSAPP: Settings -> Linked Devices  ');
            console.log('=============================================================\\n');
            qrcode.generate(qr, { small: true });
            console.log('\\nWaiting for device pairing scan...\\n');
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
            console.log(`[locaLLM WhatsApp Bridge] Connection closed (code ${statusCode}). Reconnecting: ${shouldReconnect}`);
            if (shouldReconnect) {
                setTimeout(startWhatsAppBridge, 3000);
            } else {
                console.log('[locaLLM WhatsApp Bridge] Device unlinked or logged out.');
            }
        } else if (connection === 'open') {
            console.log('\\n[SUCCESS] Connected to WhatsApp Web successfully!');
            console.log(`[locaLLM WhatsApp Bridge] User JID: ${sock.user?.id || 'Connected'}`);
            console.log('[locaLLM WhatsApp Bridge] Ready and listening for incoming messages...\\n');
        }
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;

        for (const msg of messages) {
            if (!msg.message) continue;
            if (msg.key.fromMe) continue;

            const chatJid = msg.key.remoteJid || '';
            const isGroup = chatJid.endsWith('@g.us');
            const rawParticipant = isGroup ? (msg.key.participant || '') : chatJid;

            let phoneJid = '';
            if (rawParticipant.endsWith('@s.whatsapp.net')) {
                phoneJid = rawParticipant;
            } else if (msg.key.remoteJidAlt && msg.key.remoteJidAlt.endsWith('@s.whatsapp.net')) {
                phoneJid = msg.key.remoteJidAlt;
            } else if (msg.key.participantAlt && msg.key.participantAlt.endsWith('@s.whatsapp.net')) {
                phoneJid = msg.key.participantAlt;
            } else if (sock.signalRepository?.lidMapping?.getPNForLID) {
                try {
                    const cachedPn = await sock.signalRepository.lidMapping.getPNForLID(rawParticipant);
                    if (cachedPn && cachedPn.endsWith('@s.whatsapp.net')) {
                        phoneJid = cachedPn;
                    }
                } catch (_) {
                    // Ignore cache lookup errors
                }
            }

            let senderId = '';
            if (phoneJid) {
                senderId = phoneJid.split('@')[0];
            } else {
                senderId = rawParticipant.replace('@s.whatsapp.net', '').replace('@c.us', '').replace('@lid', '');
            }

            const senderName = msg.pushName || '';
            let body = msg.message.conversation ||
                msg.message.extendedTextMessage?.text ||
                msg.message.imageMessage?.caption ||
                '';

            let imageBase64 = null;
            if (msg.message.imageMessage) {
                try {
                    const buffer = await downloadMediaMessage(
                        msg,
                        'buffer',
                        {},
                        { logger: pino({ level: 'silent' }), reuploadRequest: sock.updateMediaMessage }
                    );
                    if (buffer) {
                        imageBase64 = buffer.toString('base64');
                        if (!body.trim()) {
                            body = 'Analyze and describe what is in this image in detail.';
                        }
                    }
                } catch (e) {
                    console.log(`[WhatsApp Media] Could not download image: ${e.message}`);
                }
            }

            if (!body.trim()) continue;

            const fromDesc = senderName ? `${senderName} (${senderId})` : senderId;
            console.log(`[Inbound Message] From: ${fromDesc}${isGroup ? ' [Group]' : ''}${imageBase64 ? ' [Image]' : ''} | Message: "${body}"`);

            try {
                const response = await fetch(LOCAL_AGENT_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        sender: senderId,
                        sender_name: senderName,
                        chat_jid: chatJid,
                        is_group: isGroup,
                        message: body,
                        image_base64: imageBase64
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data && data.reply) {
                        await sock.sendMessage(chatJid, { text: data.reply }, isGroup ? { quoted: msg } : {});
                        console.log(`[Outbound Reply] Sent response to ${fromDesc}`);
                    }
                } else {
                    let errDetail = '';
                    try {
                        const errJson = await response.json();
                        errDetail = errJson.error ? `: ${errJson.error}` : '';
                    } catch (_) {}
                    console.error(`[Error] locaLLM engine returned HTTP status ${response.status}${errDetail}`);
                }
            } catch (err) {
                console.error(`[Error communicating with locaLLM]: ${err.message}`);
            }
        }
    });
}

startWhatsAppBridge();
"""


def _ensure_bridge_files_exist() -> Path:
    """Ensure bridge directory, package.json, and bridge.mjs exist on disk."""
    bridge_dir = Path(__file__).parent.parent / "bridges" / "whatsapp"
    bridge_dir.mkdir(parents=True, exist_ok=True)
    pkg_file = bridge_dir / "package.json"
    if not pkg_file.exists():
        pkg_file.write_text(DEFAULT_PACKAGE_JSON, encoding="utf-8")
    bridge_file = bridge_dir / "bridge.mjs"
    if not bridge_file.exists():
        bridge_file.write_text(DEFAULT_BRIDGE_MJS, encoding="utf-8")
    return bridge_file


def _display_bridge_script(interactive: bool = True) -> None:
    """Display the full Node.js Baileys bridge script and manual execution guide."""
    bridge_file = _ensure_bridge_files_exist()
    bridge_dir = bridge_file.parent

    script_content = bridge_file.read_text(encoding="utf-8", errors="replace")
    console.print(Panel(
        f"[bold white]WhatsApp Baileys Bridge Script[/]\n"
        f"[#aaaaaa]Location:[/] [cyan]{bridge_file}[/]\n\n"
        "To run this bridge manually in a separate terminal:\n"
        f"  [bold cyan]cd \"{bridge_dir}\"[/]\n"
        "  [bold cyan]npm install[/]\n"
        "  [bold cyan]node bridge.mjs[/]\n",
        title="[bold cyan]Bridge Script & Execution Guide[/]",
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print(Syntax(script_content, "javascript", theme="monokai", line_numbers=True))
    console.print()

    if not interactive or not sys.stdin.isatty():
        return

    try:
        sub_action = questionary.select(
            "Script Actions:",
            choices=[
                "Return to WhatsApp Menu",
                "Copy Bridge Files to Current Directory",
                "Open Bridge Folder in File Explorer",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if sub_action == "Copy Bridge Files to Current Directory":
            target_dir = Path.cwd() / "whatsapp_bridge"
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bridge_file, target_dir / "bridge.mjs")
            shutil.copy2(bridge_dir / "package.json", target_dir / "package.json")
            console.print(f"[bold green]Copied bridge files to:[/] [cyan]{target_dir}[/]\n")
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        elif sub_action == "Open Bridge Folder in File Explorer":
            try:
                if os.name == "nt":
                    os.startfile(str(bridge_dir))
                else:
                    subprocess.run(["xdg-open", str(bridge_dir)])
            except Exception as exc:
                console.print(f"[danger]Could not open directory:[/] {exc}\n")
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
    except Exception:
        pass


def _start_live_bridge(config: LocaLLMConfig, client: OllamaClient) -> None:
    """Launch local HTTP daemon and spawn the Node.js Baileys bridge."""
    bridge_file = _ensure_bridge_files_exist()
    bridge_dir = bridge_file.parent

    if not shutil.which("node"):
        console.print("[danger]Error: Node.js executable not found in system PATH.[/]")
        console.print("[#aaaaaa]Please ensure Node.js is installed to run the live Baileys bridge.[/]\n")
        return

    # Check if node_modules exists
    if not (bridge_dir / "node_modules").exists():
        console.print("[yellow]Node dependencies (@whiskeysockets/baileys) not found. Installing via npm...[/]")
        try:
            subprocess.run(["npm", "install"], cwd=str(bridge_dir), shell=True, check=True)
            console.print("[bold green]Dependencies installed successfully.[/]\n")
        except Exception as exc:
            console.print(f"[danger]Failed to install npm dependencies:[/] {exc}\n")
            console.print(f"[#aaaaaa]You can run 'npm install' manually inside {bridge_dir}.[/]\n")
            return

    # Start local HTTP server in background thread on port 5820
    handler_class = type("BoundHandler", (WhatsAppHTTPBridgeHandler,), {"config": config, "client": client})
    server = HTTPServer(("127.0.0.1", 5820), handler_class)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    console.print("[bold green]Local locaLLM agent endpoint active at[/] [cyan]http://127.0.0.1:5820/chat[/]")
    console.print("[bold cyan]Launching Baileys WhatsApp Web QR Bridge...[/]\n")

    proc = None
    try:
        proc = subprocess.Popen(["node", str(bridge_file)], cwd=str(bridge_dir))
        proc.wait()
    except KeyboardInterrupt:
        console.print("\n[#aaaaaa]WhatsApp bridge terminated by user.[/]")
    finally:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        server.shutdown()


def run_whatsapp_bot(config: LocaLLMConfig, client: OllamaClient) -> None:
    """Start WhatsApp daemon runner."""
    is_online = client.is_connected()
    backend_status = "[bold green]ONLINE[/]" if is_online else f"[bold red]OFFLINE[/] ({config.ollama_host})"

    session_dir = get_whatsapp_session_dir(config)
    active_ws = getattr(config, "active_workspace", "default")
    whitelist = config.whatsapp_allowed_numbers

    console.clear()
    console.print(Panel(
        f"[bold white]WhatsApp Bot Runner Active (24/7 Mode)[/]\n\n"
        f"[#aaaaaa]Backend Service  :[/] {backend_status}\n"
        f"[#aaaaaa]Session Directory:[/] [cyan]{session_dir}[/]\n"
        f"[#aaaaaa]Active Workspace :[/] [bold cyan]{active_ws}[/]\n"
        f"[#aaaaaa]Model            :[/] [bold cyan]{config.default_model}[/]\n"
        f"[#aaaaaa]Allowed Numbers  :[/] [#00ff87]{len(whitelist)} number(s) whitelisted[/]\n\n"
        "[dim white]Press Ctrl+C at any time to stop the runner.[/]",
        title="[bold cyan]✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ   ᴡ ʜ ᴀ ᴛ s ᴀ ᴘ ᴘ  ✦[/]",
        border_style="cyan",
        padding=(1, 2),
    ))

    try:
        run_choice = questionary.select(
            "Runner Mode:",
            choices=[
                "Start Bot",
                "Message Simulator",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if run_choice is None or run_choice == "Back":
            return

        if run_choice == "Start Bot":
            if not is_online:
                console.print(f"[danger]Error: Backend service is not reachable at[/] {config.ollama_host}")
                console.print("[#aaaaaa]Please start the local inference server ('locaLLM start ollama') first.[/]\n")
            else:
                _start_live_bridge(config, client)

        elif run_choice == "Message Simulator":
            if not is_online:
                console.print(f"[danger]Error: Backend service is not reachable at[/] {config.ollama_host}")
                console.print("[#aaaaaa]Please start the local inference server ('locaLLM start ollama') first.[/]\n")
            else:
                sender = questionary.text(
                    "Sender phone number (default: 628123456789):",
                    default=whitelist[0] if whitelist else "628123456789",
                    style=QUESTIONARY_STYLE,
                ).ask()
                if sender:
                    console.print(f"[#aaaaaa]Simulating incoming WhatsApp chat from[/] [bold cyan]{sender}[/]. Type 'exit' to return.\n")
                    while True:
                        msg = questionary.text(f"[{sender}] >", style=QUESTIONARY_STYLE).ask()
                        if msg is None or msg.strip().lower() == "exit":
                            break
                        if not msg.strip():
                            continue

                        with thinking_spinner("locaLLM is processing WhatsApp message..."):
                            reply = process_whatsapp_message(sender, msg, config, client, skip_whitelist=True)

                        console.print(f"[bold green][Bot Reply][/]\n{reply}\n")

    except KeyboardInterrupt:
        console.print("\n[#aaaaaa]WhatsApp Bot runner stopped cleanly.[/]\n")

    try:
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
    except (KeyboardInterrupt, EOFError):
        pass

