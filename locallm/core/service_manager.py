"""Service manager to start, stop, and inspect local inference backends."""

import shutil
import subprocess
import time
from typing import Dict, Optional, Tuple, Any
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


def is_ollama_installed() -> bool:
    """Check if Ollama executable is available in system PATH."""
    return shutil.which("ollama") is not None


def start_ollama_service() -> Tuple[bool, str]:
    """Start Ollama server process explicitly upon user request with environment inheritance."""
    import os
    import sys
    from pathlib import Path

    if is_ollama_running(max_cache_age=0.0):
        return True, "Ollama service is already running."

    ollama_cmd = ["ollama", "serve"]
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            ollama_app_exe = Path(local_app_data) / "Programs" / "Ollama" / "ollama app.exe"
            ollama_cli_exe = Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe"
            if ollama_app_exe.exists():
                ollama_cmd = [str(ollama_app_exe)]
            elif ollama_cli_exe.exists():
                ollama_cmd = [str(ollama_cli_exe), "serve"]

    if not shutil.which(ollama_cmd[0]) and not Path(ollama_cmd[0]).exists():
        return False, "Ollama CLI or application executable not found in system PATH."

    try:
        flags = 0
        if hasattr(subprocess, "DETACHED_PROCESS") and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            flags |= subprocess.CREATE_NO_WINDOW

        env = dict(os.environ)
        proc = subprocess.Popen(
            ollama_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
            env=env,
        )

        for _ in range(15):
            time.sleep(0.25)
            _service_cache.clear()
            if is_ollama_running(max_cache_age=0.0):
                return True, "Ollama service started successfully in background."

        if proc.poll() is not None:
            return False, f"Ollama process exited with code {proc.returncode}."

        return True, f"Ollama launched (PID {proc.pid}) and initializing in background."
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


def is_api_server_running(
    host: str = "127.0.0.1",
    port: int = 8080,
    max_cache_age: float = 3.0,
) -> bool:
    """Check if the local OpenAI-compatible API Gateway server is actively listening."""
    import socket
    now = time.time()
    cache_key = f"api_server_{host}_{port}"
    if cache_key in _service_cache:
        val, ts = _service_cache[cache_key]
        if now - ts < max_cache_age:
            return val

    # 1. Fast HTTP probe on /health
    try:
        url = f"http://{host}:{port}/health"
        with httpx.Client(timeout=0.6) as client:
            res = client.get(url)
            if res.status_code == 200:
                _service_cache[cache_key] = (True, now)
                return True
    except Exception:
        pass

    # 2. Direct TCP socket connection probe
    try:
        with socket.create_connection((host, int(port)), timeout=0.3):
            _service_cache[cache_key] = (True, now)
            return True
    except Exception:
        pass

    _service_cache[cache_key] = (False, now)
    return False



def start_api_server_service(
    config: Optional[Any] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> Tuple[bool, str]:
    """Start locaLLM API Gateway server daemon in background."""
    import os
    import sys
    from pathlib import Path
    from locallm.config import get_config_dir

    target_host = host or getattr(config, "server_host", "127.0.0.1")
    target_port = port or getattr(config, "server_port", 8080)

    if is_api_server_running(target_host, target_port):
        return True, f"API Gateway server is already running on http://{target_host}:{target_port}/v1"

    repo_root = Path(__file__).resolve().parent.parent.parent

    # Detect the best python or locallm executable in local environment
    if sys.platform == "win32":
        venv_locallm = repo_root / ".venv" / "Scripts" / "locallm.exe"
        venv_pythonw = repo_root / ".venv" / "Scripts" / "pythonw.exe"
        venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    else:
        venv_locallm = repo_root / ".venv" / "bin" / "locallm"
        venv_pythonw = None
        venv_python = repo_root / ".venv" / "bin" / "python"

    if sys.platform == "win32" and venv_pythonw and venv_pythonw.exists():
        cmd = [str(venv_pythonw), "-m", "locallm", "serve", "--host", str(target_host), "--port", str(target_port)]
    elif venv_locallm.exists():
        cmd = [str(venv_locallm), "serve", "--host", str(target_host), "--port", str(target_port)]
    elif venv_python.exists():
        cmd = [str(venv_python), "-m", "locallm", "serve", "--host", str(target_host), "--port", str(target_port)]
    else:
        cmd = [sys.executable, "-m", "locallm", "serve", "--host", str(target_host), "--port", str(target_port)]

    try:
        flags = 0
        if hasattr(subprocess, "DETACHED_PROCESS") and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            flags |= subprocess.CREATE_NO_WINDOW

        log_dir = get_config_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = open(log_dir / "server.log", "a", encoding="utf-8")

        env = dict(os.environ)
        current_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{current_pp}" if current_pp else str(repo_root)

        kwargs: Dict[str, Any] = {
            "stdout": log_file,
            "stderr": log_file,
            "stdin": subprocess.DEVNULL,
            "cwd": str(repo_root),
            "env": env,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = flags
        else:
            kwargs["start_new_session"] = True

        proc = subprocess.Popen(cmd, **kwargs)

        for _ in range(12):
            time.sleep(0.25)
            _service_cache.clear()
            if is_api_server_running(target_host, target_port, max_cache_age=0.0):
                return True, f"API Gateway server started in background at http://{target_host}:{target_port}/v1"

        if proc.poll() is not None:
            return False, f"API Gateway server exited with code {proc.returncode}. See {log_dir / 'server.log'}"

        return False, f"API Gateway server launched (PID {proc.pid}) but did not respond on port {target_port} within timeout. See {log_dir / 'server.log'}"
    except Exception as exc:
        return False, f"Failed to start API Gateway server: {exc}"


def stop_api_server_service(
    host: str = "127.0.0.1",
    port: int = 8080,
) -> Tuple[bool, str]:
    """Stop running locaLLM API Gateway background process."""
    stopped_count = 0

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or []).lower()
            if ("locallm" in cmdline and "serve" in cmdline) or ("api_server" in cmdline and "python" in cmdline):
                for child in proc.children(recursive=True):
                    try:
                        child.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                proc.terminate()
                stopped_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    _service_cache.clear()
    if stopped_count > 0:
        return True, f"Stopped {stopped_count} background API server process(es)."
    return False, "No active API server process found to stop."


def get_all_services_status(
    ollama_host: str = "http://127.0.0.1:11434",
    custom_platforms: Optional[list] = None,
    server_host: str = "127.0.0.1",
    server_port: int = 8080,
) -> Dict[str, bool]:
    """Return running state map for configured local inference services."""
    statuses: Dict[str, bool] = {
        "Ollama": is_ollama_running(ollama_host),
        "API Gateway Server": is_api_server_running(server_host, server_port),
    }
    if custom_platforms:
        for p in custom_platforms:
            statuses[p.name] = is_custom_platform_reachable(
                p.api_base, getattr(p, "api_key", "")
            )
    return statuses
