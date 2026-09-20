/**
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
        const match = errorStr.match(/(\d+)\.(\d+)/);
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
    console.log('\n[locaLLM WhatsApp Bridge] Initializing Baileys engine...');
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
    console.log(`[locaLLM WhatsApp Bridge] Agent Endpoint: ${LOCAL_AGENT_URL}\n`);

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
            console.log('\n=============================================================');
            console.log('  SCAN THIS QR CODE IN WHATSAPP: Settings -> Linked Devices  ');
            console.log('=============================================================\n');
            qrcode.generate(qr, { small: true });
            console.log('\nWaiting for device pairing scan...\n');
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
            console.log('\n[SUCCESS] Connected to WhatsApp Web successfully!');
            console.log(`[locaLLM WhatsApp Bridge] User JID: ${sock.user?.id || 'Connected'}`);
            console.log('[locaLLM WhatsApp Bridge] Ready and listening for incoming messages...\n');
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

            // In group chats, participant contains the sender JID.
            // In direct chats, remoteJid contains the sender JID.
            const rawParticipant = isGroup ? (msg.key.participant || '') : chatJid;

            // WhatsApp Multi-Device privacy uses LID (e.g. 264342452871356@lid).
            // Check if phone number is available in remoteJidAlt, participantAlt, or Baileys signal cache.
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

            // Clean identifier: phone number preferred, fallback to LID
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
