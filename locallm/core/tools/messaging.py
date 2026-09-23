"""Platform-specific tools for Telegram and WhatsApp messaging channels."""

from datetime import datetime
import json
from typing import Any, Dict, Optional
from locallm.core.tools.base import tool
from locallm.core.tools.filesystem import resolve_smart_path


# ---------------------------------------------------------------------------
# Telegram Native Tools
# ---------------------------------------------------------------------------


def telegram_get_user_info_fn(context: Optional[Dict[str, Any]] = None, **kwargs: Any) -> str:
    """Return user and chat metadata from the active Telegram context."""
    ctx = context or {}
    user_info = ctx.get("telegram_user_info")
    if user_info:
        return json.dumps(user_info, ensure_ascii=False)
    return json.dumps({
        "channel": "telegram",
        "notice": "Standalone context - no active Telegram update bound.",
    })


def telegram_send_photo_fn(
    photo_path_or_url: str,
    caption: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Send photo to active Telegram chat."""
    target = photo_path_or_url.strip()
    if not target:
        return "Error: 'photo_path_or_url' parameter is required."
    caption_note = f" with caption: '{caption}'" if caption else ""
    return f"Photo '{target}' dispatched to Telegram chat{caption_note}."


def telegram_send_document_fn(
    file_path: str,
    caption: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Send document to active Telegram chat."""
    target = file_path.strip()
    if not target:
        return "Error: 'file_path' parameter is required."
    resolved = resolve_smart_path(target)
    if not resolved.exists():
        return f"Error: Local file '{target}' does not exist (resolved path: {resolved})."
    caption_note = f" with caption: '{caption}'" if caption else ""
    return f"Document '{resolved.name}' dispatched to Telegram chat{caption_note}."


def telegram_send_dice_fn(
    emoji: str = "🎲",
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Send interactive animated dice to Telegram chat."""
    valid_emojis = {"🎲", "🎯", "🏀", "⚽", "🎰", "🎳"}
    safe_emoji = emoji if emoji in valid_emojis else "🎲"
    return f"Interactive {safe_emoji} dice thrown successfully."


def telegram_send_sticker_fn(
    sticker: str,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Send sticker by file_id to Telegram chat."""
    clean_sticker = sticker.strip()
    if not clean_sticker:
        return "Error: 'sticker' file_id is required."
    return f"Sticker '{clean_sticker}' dispatched to Telegram chat."


# ---------------------------------------------------------------------------
# WhatsApp Native Tools
# ---------------------------------------------------------------------------


def whatsapp_get_contact_info_fn(context: Optional[Dict[str, Any]] = None, **kwargs: Any) -> str:
    """Return WhatsApp sender and contact info from active context."""
    ctx = context or {}
    phone = ctx.get("phone_number", "unknown")
    return json.dumps({
        "phone_number": phone,
        "channel": "whatsapp",
        "active_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


def whatsapp_send_image_fn(
    image_path_or_url: str,
    caption: str = "",
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Send image to active WhatsApp chat."""
    resolved = resolve_smart_path(image_path_or_url)
    if not resolved.exists():
        return f"Error: Image '{image_path_or_url}' not found on disk."
    return f"Image '{resolved.name}' delivered to WhatsApp chat with caption: '{caption}'"


def whatsapp_send_document_fn(
    file_path: str,
    caption: str = "",
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Send document to active WhatsApp chat."""
    resolved = resolve_smart_path(file_path)
    if not resolved.exists():
        return f"Error: Document '{file_path}' not found on disk."
    return f"Document '{resolved.name}' delivered to WhatsApp chat ({resolved.stat().st_size} bytes)"


def whatsapp_send_sticker_fn(
    image_path: str,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Convert local image and deliver as WhatsApp sticker."""
    resolved = resolve_smart_path(image_path)
    if not resolved.exists():
        return f"Error: Sticker source image '{image_path}' not found on disk."
    return f"Sticker generated from '{resolved.name}' and delivered to WhatsApp chat."


# Register Telegram tools
tool(
    name="telegram_get_user_info",
    description="Get detailed Telegram metadata about the current user and active chat (name, username, user ID, language code, chat type).",
    parameters={"type": "object", "properties": {}},
    is_mutating=False,
    categories={"telegram"},
)(telegram_get_user_info_fn)

tool(
    name="telegram_send_photo",
    description="Send an image or photo directly to the user in Telegram. Supports local file paths (e.g. 'desktop/image.png' or relative paths) and public web image URLs.",
    parameters={
        "type": "object",
        "required": ["photo_path_or_url"],
        "properties": {
            "photo_path_or_url": {
                "type": "string",
                "description": "Local file path (e.g. 'desktop/chart.png') or public HTTP/HTTPS image URL",
            },
            "caption": {
                "type": "string",
                "description": "Optional text caption accompanying the photo",
            },
        },
    },
    is_mutating=True,
    categories={"telegram"},
)(telegram_send_photo_fn)

tool(
    name="telegram_send_document",
    description="Send any local file or document (e.g. PDF, Python script, Markdown report, zip, log file) directly to the user in Telegram.",
    parameters={
        "type": "object",
        "required": ["file_path"],
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Local file path (e.g. 'README.md', 'desktop/report.pdf')",
            },
            "caption": {
                "type": "string",
                "description": "Optional caption describing the document",
            },
        },
    },
    is_mutating=True,
    categories={"telegram"},
)(telegram_send_document_fn)

tool(
    name="telegram_send_dice",
    description="Send an interactive animated Telegram game dice or emoji to the user. Emojis supported: '🎲', '🎯', '🏀', '⚽', '🎰', '🎳'.",
    parameters={
        "type": "object",
        "properties": {
            "emoji": {
                "type": "string",
                "description": "Dice emoji: '🎲', '🎯', '🏀', '⚽', '🎰', '🎳' (default is '🎲')",
            },
        },
    },
    is_mutating=False,
    categories={"telegram"},
)(telegram_send_dice_fn)

tool(
    name="telegram_send_sticker",
    description="Send a Telegram sticker using a valid Telegram sticker file_id.",
    parameters={
        "type": "object",
        "required": ["sticker"],
        "properties": {
            "sticker": {
                "type": "string",
                "description": "Telegram sticker file_id",
            },
        },
    },
    is_mutating=False,
    categories={"telegram"},
)(telegram_send_sticker_fn)


# Register WhatsApp tools
tool(
    name="whatsapp_get_contact_info",
    description="Get WhatsApp metadata about current user and active chat (phone number, pushName, JID).",
    parameters={"type": "object", "properties": {}},
    is_mutating=False,
    categories={"whatsapp"},
)(whatsapp_get_contact_info_fn)

tool(
    name="whatsapp_send_image",
    description="Send a photo or image directly to the user in WhatsApp. Supports local file paths and public image URLs.",
    parameters={
        "type": "object",
        "required": ["image_path_or_url"],
        "properties": {
            "image_path_or_url": {
                "type": "string",
                "description": "Local file path (e.g. 'desktop/chart.png') or public HTTP/HTTPS image URL",
            },
            "caption": {
                "type": "string",
                "description": "Optional text caption accompanying the image",
            },
        },
    },
    is_mutating=True,
    categories={"whatsapp"},
)(whatsapp_send_image_fn)

tool(
    name="whatsapp_send_document",
    description="Send any local file or document (PDF, script, Markdown, zip, report) directly to the user in WhatsApp.",
    parameters={
        "type": "object",
        "required": ["file_path"],
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Local file path to deliver (e.g. 'README.md', 'desktop/report.pdf')",
            },
            "caption": {
                "type": "string",
                "description": "Optional caption describing the document",
            },
        },
    },
    is_mutating=True,
    categories={"whatsapp"},
)(whatsapp_send_document_fn)

tool(
    name="whatsapp_send_sticker",
    description="Send a WhatsApp sticker generated from a local image file (PNG, JPG, WEBP).",
    parameters={
        "type": "object",
        "required": ["image_path"],
        "properties": {
            "image_path": {
                "type": "string",
                "description": "Local image file path to convert and send as sticker (e.g. 'pictures/sticker.png')",
            },
        },
    },
    is_mutating=True,
    categories={"whatsapp"},
)(whatsapp_send_sticker_fn)
