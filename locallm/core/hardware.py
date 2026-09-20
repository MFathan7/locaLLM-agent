"""Hardware and VRAM detection utilities for local model sizing."""

import shutil
import subprocess
import time
from typing import NamedTuple, Optional, Tuple
import psutil

_cached_gpu_info: Optional["GPUInfo"] = None
_last_gpu_check: float = 0.0


class GPUInfo(NamedTuple):
    """Container for GPU status."""

    name: str
    total_vram_mb: int
    free_vram_mb: int
    used_vram_mb: int


class SystemResources(NamedTuple):
    """Container for system hardware resources."""

    gpu: Optional[GPUInfo]
    ram_total_gb: float
    ram_available_gb: float


def get_gpu_info(force_refresh: bool = False) -> Optional[GPUInfo]:
    """Detect NVIDIA GPU information using nvidia-smi with 10s caching."""
    global _cached_gpu_info, _last_gpu_check

    now = time.time()
    if not force_refresh and _cached_gpu_info is not None and (now - _last_gpu_check < 10.0):
        return _cached_gpu_info

    if not shutil.which("nvidia-smi"):
        _cached_gpu_info = None
        _last_gpu_check = now
        return None

    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.free,memory.used",
            "--format=csv,noheader,nounits",
        ]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
            creationflags=flags,
        )
        output = result.stdout.strip()
        if not output:
            return None

        line = output.splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            return None

        gpu = GPUInfo(
            name=parts[0],
            total_vram_mb=int(parts[1]),
            free_vram_mb=int(parts[2]),
            used_vram_mb=int(parts[3]),
        )
        _cached_gpu_info = gpu
        _last_gpu_check = now
        return gpu
    except Exception:
        _cached_gpu_info = None
        _last_gpu_check = now
        return None


def get_system_resources() -> SystemResources:
    """Retrieve combined GPU and RAM status."""
    mem = psutil.virtual_memory()
    return SystemResources(
        gpu=get_gpu_info(),
        ram_total_gb=round(mem.total / (1024**3), 1),
        ram_available_gb=round(mem.available / (1024**3), 1),
    )


def check_vram_compatibility(model_size_bytes: int) -> Tuple[bool, str]:
    """Determine if a model size fits comfortably in available VRAM.

    Returns:
        Tuple[bool, str]: (is_compatible, status_message)
    """
    gpu = get_gpu_info()
    model_mb = model_size_bytes / (1024 * 1024)
    model_gb = model_mb / 1024

    if not gpu:
        return False, f"No GPU detected (CPU mode, ~{model_gb:.1f} GB RAM)"

    # User formula: Required VRAM = Model Size + 2 GB (KV Cache & context overhead)
    buffer_gb = 2.0
    required_gb = model_gb + buffer_gb
    total_gb = gpu.total_vram_mb / 1024
    free_gb = gpu.free_vram_mb / 1024

    if required_gb <= free_gb:
        return True, f"FIT (Free VRAM OK: {required_gb:.1f} GB <= {free_gb:.1f} GB Free)"

    if required_gb <= total_gb:
        return True, f"FIT (Fits Total VRAM: {required_gb:.1f} GB <= {total_gb:.1f} GB Total)"

    return False, f"NOT FIT (Exceeds: {required_gb:.1f} GB > {total_gb:.1f} GB, offload needed)"
