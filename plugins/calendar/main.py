"""Calendar plugin implementation for locaLLM."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _get_storage_path() -> Path:
    """Return path to calendar events JSON store."""
    base_dir = Path.home() / ".locallm"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "calendar_events.json"


def _load_events() -> List[Dict[str, Any]]:
    """Load events list from JSON file."""
    path = _get_storage_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_events(events: List[Dict[str, Any]]) -> None:
    """Save events list to JSON file."""
    path = _get_storage_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)


def get_calendar_events(date: Optional[str] = None) -> str:
    """Retrieve scheduled calendar events, optionally filtered by date (YYYY-MM-DD)."""
    events = _load_events()
    if not events:
        return "No scheduled events found on the calendar."

    if date:
        clean_date = date.strip()
        matched = [e for e in events if e.get("date") == clean_date]
        if not matched:
            return f"No events scheduled for {clean_date}."
        events = matched

    # Sort events by date and time
    events.sort(key=lambda e: (e.get("date", ""), e.get("time", "")))

    lines = [
        f"Found {len(events)} calendar event(s):",
        "",
        "| Date | Time | Title | Description |",
        "|---|---|---|---|",
    ]
    for e in events:
        edate = e.get("date", "-")
        etime = e.get("time", "All day") or "All day"
        etitle = e.get("title", "Untitled")
        edesc = e.get("description", "-") or "-"
        lines.append(f"| {edate} | {etime} | {etitle} | {edesc} |")

    return "\n".join(lines)


def add_calendar_event(title: str, date: str, time: str = "", description: str = "") -> str:
    """Add a new calendar event."""
    clean_title = title.strip()
    clean_date = date.strip()
    if not clean_title:
        return "Error: Event title cannot be empty."
    if not clean_date:
        return "Error: Event date cannot be empty."

    events = _load_events()
    new_event = {
        "title": clean_title,
        "date": clean_date,
        "time": time.strip(),
        "description": description.strip(),
    }
    events.append(new_event)
    _save_events(events)

    time_str = f" at {time.strip()}" if time.strip() else ""
    return f"Successfully scheduled '{clean_title}' on {clean_date}{time_str}."


def delete_calendar_event(title: str) -> str:
    """Delete a calendar event matching title."""
    clean_title = title.strip().lower()
    if not clean_title:
        return "Error: Title to delete cannot be empty."

    events = _load_events()
    before_count = len(events)
    remaining = [e for e in events if clean_title not in e.get("title", "").lower()]

    if len(remaining) == before_count:
        return f"No calendar event matching '{title}' was found."

    deleted_count = before_count - len(remaining)
    _save_events(remaining)
    return f"Successfully removed {deleted_count} event(s) matching '{title}'."
