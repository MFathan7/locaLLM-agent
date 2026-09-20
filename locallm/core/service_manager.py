"""Service manager to start, stop, and inspect local inference backends."""

import shutil
import subprocess
import time
from typing import Dict, Optional, Tuple
import httpx
import psutil

_service_cache: Dict[str, Tuple[bool, float]] = {}


def is_ollama_running(host: str = "http://127.0.0.1:11434", max_cache_age: float = 3.0) -> bool:
    """Check if Ollama server is running with 3s cache."""
    now = time.time()
    cache_key = f"ollama_{host}"
    if cache_key in _service_cache:
        val, ts = _service_cache[cache_key]
        if now - ts < max_cache_age:
            return val

    try:
        with httpx.Client(base_url=host, timeout=0.4) as client:
            res = client.get("/api/version")
            is_up = (res.status_code == 200)
            _service_cache[cache_key] = (is_up, now)
            return is_up
    except Exception:
        # Check process table quickly as fallback
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info["name"] or ""
                if name.lower() in ("ollama.exe", "ollama app.exe", "ollama"):
                    _service_cache[cache_key] = (True, now)
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        _service_cache[cache_key] = (False, now)
        return False


def start_ollama_service() -> Tuple[bool, str]:
    """Start Ollama server process explicitly upon user request."""
    if is_ollama_running():
        return True, "Ollama service is already running."

    if not shutil.which("ollama"):
        return False, "Ollama CLI executable not found in system PATH."

    try:
        flags = 0
        if hasattr(subprocess, "DETACHED_PROCESS") and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            flags |= subprocess.CREATE_NO_WINDOW

        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        return True, "Ollama service started successfully in background."
    except Exception as exc:
        return False, f"Failed to start Ollama: {exc}"


def stop_ollama_service(host: str = "http://127.0.0.1:11434") -> Tuple[bool, str]:
    """Terminate Ollama server and llama-server worker processes cleanly, unloading VRAM first."""
    # 1. Attempt graceful model ejection from VRAM via Ollama API
    try:
        with httpx.Client(base_url=host, timeout=1.5) as client:
            ps_res = client.get("/api/ps")
            if ps_res.status_code == 200:
                for m in ps_res.json().get("models", []):
                    m_name = m.get("name") or m.get("model")
                    if m_name:
                        client.post("/api/generate", json={"model": m_name, "keep_alive": 0}, timeout=1.5)
    except Exception:
        pass

    killed_count = 0
    target_names = {
        "ollama.exe",
        "ollama app.exe",
        "ollama",
        "llama-server.exe",
        "llama-server",
        "ollama_llama_server.exe",
        "llama-runner.exe",
    }

    # 2. Terminate matching processes and any child processes
    procs_to_kill = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = proc.info["name"] or ""
            if name.lower() in target_names:
                procs_to_kill.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    for proc in procs_to_kill:
        try:
            # Terminate children first
            for child in proc.children(recursive=True):
                try:
                    child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            proc.terminate()
            killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Reset cache
    _service_cache.clear()

    if killed_count > 0:
        return True, f"Stopped {killed_count} Ollama & runner process(es) and released VRAM."
    return False, "No active Ollama or runner process found to stop."



def is_custom_platform_reachable(
    api_base: str,
    api_key: str = "",
    timeout: float = 1.0,
    max_cache_age: float = 3.0,
) -> bool:
    """Check if a custom OpenAI-compatible platform endpoint is reachable with 3s cache."""
    now = time.time()
    cache_key = f"custom_{api_base}"
    if cache_key in _service_cache:
        val, ts = _service_cache[cache_key]
        if now - ts < max_cache_age:
            return val

    try:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key and api_key != "not-needed" else {}
        url = f"{api_base.rstrip('/')}/models"
        with httpx.Client(timeout=timeout, headers=headers) as client:
            res = client.get(url)
            is_up = (res.status_code in (200, 401, 403))
            _service_cache[cache_key] = (is_up, now)
            return is_up
    except Exception:
        _service_cache[cache_key] = (False, now)
        return False


def get_all_services_status(
    ollama_host: str = "http://127.0.0.1:11434",
    custom_platforms: Optional[list] = None,
) -> Dict[str, bool]:
    """Return running state map for configured local inference services."""
    statuses: Dict[str, bool] = {
        "Ollama": is_ollama_running(ollama_host),
    }
    if custom_platforms:
        for p in custom_platforms:
            statuses[p.name] = is_custom_platform_reachable(
                p.api_base, getattr(p, "api_key", "")
            )
    return statuses
