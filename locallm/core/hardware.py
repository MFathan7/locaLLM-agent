"""Hardware and VRAM detection utilities for local model sizing."""

import shutil
import subprocess
import time
from typing import Any, List, NamedTuple, Optional, Tuple, Union
import psutil

_cached_gpu_info: Optional["GPUInfo"] = None
_last_gpu_check: float = 0.0
_cached_gpu_ext_info: Optional["GPUExtendedInfo"] = None
_last_gpu_ext_check: float = 0.0


class GPUInfo(NamedTuple):
    """Container for GPU status."""

    name: str
    total_vram_mb: int
    free_vram_mb: int
    used_vram_mb: int


class GPUExtendedInfo(NamedTuple):
    """Container for detailed live GPU status including utilization and temperature."""

    name: str
    total_vram_mb: int
    free_vram_mb: int
    used_vram_mb: int
    utilization_pct: int
    temperature_c: int


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


def get_gpu_extended_info(force_refresh: bool = False) -> Optional[GPUExtendedInfo]:
    """Detect NVIDIA GPU status with utilization and temperature (1s cache)."""
    global _cached_gpu_ext_info, _last_gpu_ext_check

    now = time.time()
    if not force_refresh and _cached_gpu_ext_info is not None and (now - _last_gpu_ext_check < 1.0):
        return _cached_gpu_ext_info

    if not shutil.which("nvidia-smi"):
        _cached_gpu_ext_info = None
        _last_gpu_ext_check = now
        return None

    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.free,memory.used,utilization.gpu,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
            creationflags=flags,
        )
        output = result.stdout.strip()
        if not output:
            return None

        line = output.splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 6:
            return None

        info = GPUExtendedInfo(
            name=parts[0],
            total_vram_mb=int(parts[1]),
            free_vram_mb=int(parts[2]),
            used_vram_mb=int(parts[3]),
            utilization_pct=int(parts[4]) if parts[4].isdigit() else 0,
            temperature_c=int(parts[5]) if parts[5].isdigit() else 0,
        )
        _cached_gpu_ext_info = info
        _last_gpu_ext_check = now
        return info
    except Exception:
        _cached_gpu_ext_info = None
        _last_gpu_ext_check = now
        return None


def get_system_resources() -> SystemResources:
    """Retrieve combined GPU and RAM status."""
    mem = psutil.virtual_memory()
    return SystemResources(
        gpu=get_gpu_info(),
        ram_total_gb=round(mem.total / (1024**3), 1),
        ram_available_gb=round(mem.available / (1024**3), 1),
    )


class VRAMSizingResult(NamedTuple):
    """Container for detailed VRAM breakdown and model compatibility."""

    model_weights_gb: float
    kv_cache_gb: float
    cuda_overhead_gb: float
    total_vram_gb: float
    usable_vram_gb: float
    headroom_gb: float
    is_fit: bool
    status: str
    status_message: str
    max_context_tokens: int
    context_tokens: int
    bytes_per_token: int


_DEFAULT_GPU_SENTINEL = object()


def calculate_vram_breakdown(
    model_size_bytes: int,
    context_tokens: int = 8192,
    layers: Optional[int] = None,
    kv_heads: Optional[Union[int, List[int]]] = None,
    head_dim: Optional[int] = None,
    precision_bytes: int = 2,
    cuda_overhead_gb: float = 0.6,
    gpu_info: Any = _DEFAULT_GPU_SENTINEL,
    sliding_window: Optional[int] = None,
    swa_pattern: Optional[List[bool]] = None,
    head_dim_swa: Optional[int] = None,
) -> VRAMSizingResult:
    """Calculate exact KV cache, total inference VRAM, headroom, and max context tokens.

    Supports GQA and Sliding Window Attention (SWA) architecture scaling.
    """
    gpu = get_gpu_info() if gpu_info is _DEFAULT_GPU_SENTINEL else gpu_info
    model_weights_gb = round(model_size_bytes / (1024**3), 3)

    # Resolve architecture parameters (with defensive heuristic fallbacks if missing)
    if layers is None or layers <= 0:
        if model_weights_gb <= 4.0:
            layers = 28
        elif model_weights_gb <= 9.0:
            layers = 32
        elif model_weights_gb <= 16.0:
            layers = 40
        else:
            layers = 64

    if head_dim is None or head_dim <= 0:
        head_dim = 128

    # Calculate total channels and KV cache bytes (SWA-aware)
    if swa_pattern and isinstance(kv_heads, list) and len(kv_heads) == len(swa_pattern):
        window_size = sliding_window or 1024
        total_kv_bytes = 0
        swa_fixed_bytes = 0
        full_bytes_per_token = 0

        for i, h in enumerate(kv_heads):
            is_swa = bool(swa_pattern[i])
            dim = head_dim_swa if (is_swa and head_dim_swa) else head_dim
            if is_swa:
                layer_tokens = min(context_tokens, window_size)
                total_kv_bytes += 2 * h * dim * max(1, precision_bytes) * layer_tokens
                swa_fixed_bytes += 2 * h * dim * max(1, precision_bytes) * window_size
            else:
                total_kv_bytes += 2 * h * dim * max(1, precision_bytes) * context_tokens
                full_bytes_per_token += 2 * h * dim * max(1, precision_bytes)

        kv_cache_bytes = total_kv_bytes
        bytes_per_token = (
            int(total_kv_bytes // max(1, context_tokens))
            if context_tokens > 0
            else full_bytes_per_token
        )
    else:
        if isinstance(kv_heads, list) and len(kv_heads) > 0:
            total_channels = sum(h for h in kv_heads if isinstance(h, int)) * head_dim
        else:
            if kv_heads is None or (isinstance(kv_heads, int) and kv_heads <= 0):
                kv_heads = 8  # Standard modern GQA head count
            total_channels = layers * kv_heads * head_dim

        bytes_per_token = 2 * total_channels * max(1, precision_bytes)
        kv_cache_bytes = bytes_per_token * max(0, context_tokens)
        swa_fixed_bytes = 0
        full_bytes_per_token = bytes_per_token

    kv_cache_gb = round(kv_cache_bytes / (1024**3), 3)
    total_vram_gb = round(model_weights_gb + kv_cache_gb + cuda_overhead_gb, 3)

    if not gpu:
        return VRAMSizingResult(
            model_weights_gb=model_weights_gb,
            kv_cache_gb=kv_cache_gb,
            cuda_overhead_gb=cuda_overhead_gb,
            total_vram_gb=total_vram_gb,
            usable_vram_gb=0.0,
            headroom_gb=-total_vram_gb,
            is_fit=False,
            status="CPU MODE",
            status_message=f"No GPU detected (CPU mode, ~{total_vram_gb:.1f} GB RAM)",
            max_context_tokens=0,
            context_tokens=context_tokens,
            bytes_per_token=bytes_per_token,
        )

    usable_vram_gb = round(gpu.free_vram_mb / 1024, 3)
    total_gpu_gb = round(gpu.total_vram_mb / 1024, 3)
    headroom_gb = round(usable_vram_gb - total_vram_gb, 3)

    # Max context tokens
    max_kv_allowed_gb = usable_vram_gb - model_weights_gb - cuda_overhead_gb
    if max_kv_allowed_gb > 0:
        max_kv_allowed_bytes = max_kv_allowed_gb * (1024**3)
        if swa_pattern and full_bytes_per_token > 0:
            rem_bytes = max_kv_allowed_bytes - swa_fixed_bytes
            if rem_bytes > 0:
                max_context_tokens = int(rem_bytes // full_bytes_per_token)
            else:
                max_context_tokens = int(max_kv_allowed_bytes // max(1, bytes_per_token))
        elif bytes_per_token > 0:
            max_context_tokens = int(max_kv_allowed_bytes // bytes_per_token)
        else:
            max_context_tokens = 0
    else:
        max_context_tokens = 0

    if total_vram_gb <= usable_vram_gb:
        is_fit = True
        status = "100% GPU"
        status_message = (
            f"FIT (100% GPU, +{headroom_gb:.1f} GB Free, max ~{max_context_tokens:,} ctx)"
        )
    elif total_vram_gb <= total_gpu_gb:
        is_fit = True
        status = "FIT (RELOAD)"
        status_message = (
            f"FIT (Fits Total VRAM: {total_vram_gb:.1f} GB <= {total_gpu_gb:.1f} GB Total)"
        )
    else:
        is_fit = False
        status = "SPILLOVER"
        status_message = (
            f"NOT FIT (SPILLOVER: Need {total_vram_gb:.1f} GB > {usable_vram_gb:.1f} GB Free, offload needed)"
        )

    return VRAMSizingResult(
        model_weights_gb=model_weights_gb,
        kv_cache_gb=kv_cache_gb,
        cuda_overhead_gb=cuda_overhead_gb,
        total_vram_gb=total_vram_gb,
        usable_vram_gb=usable_vram_gb,
        headroom_gb=headroom_gb,
        is_fit=is_fit,
        status=status,
        status_message=status_message,
        max_context_tokens=max_context_tokens,
        context_tokens=context_tokens,
        bytes_per_token=bytes_per_token,
    )


def check_vram_compatibility(
    model_size_bytes: int,
    context_tokens: int = 8192,
    layers: Optional[int] = None,
    kv_heads: Optional[Union[int, List[int]]] = None,
    head_dim: Optional[int] = None,
    precision_bytes: int = 2,
    cuda_overhead_gb: float = 0.6,
    sliding_window: Optional[int] = None,
    swa_pattern: Optional[List[bool]] = None,
    head_dim_swa: Optional[int] = None,
) -> Tuple[bool, str]:
    """Determine if a model size and KV cache fit comfortably in available VRAM.

    Backwards-compatible wrapper around calculate_vram_breakdown.

    Returns:
        Tuple[bool, str]: (is_compatible, status_message)
    """
    res = calculate_vram_breakdown(
        model_size_bytes=model_size_bytes,
        context_tokens=context_tokens,
        layers=layers,
        kv_heads=kv_heads,
        head_dim=head_dim,
        precision_bytes=precision_bytes,
        cuda_overhead_gb=cuda_overhead_gb,
        sliding_window=sliding_window,
        swa_pattern=swa_pattern,
        head_dim_swa=head_dim_swa,
    )
    return res.is_fit, res.status_message
