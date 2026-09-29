"""HTTP client for Ollama API communication."""

import json
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
import httpx


class OllamaClient:
    """Synchronous client for Ollama local API."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: float = 180.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._cached_version: Optional[str] = None
        self._cached_connected: Optional[bool] = None
        self._last_check_time: float = 0.0

    def is_connected(self, max_cache_age: float = 5.0) -> bool:
        """Check if Ollama server is reachable with caching."""
        import time
        now = time.time()
        if self._cached_connected is not None and (now - self._last_check_time < max_cache_age):
            return self._cached_connected

        try:
            with httpx.Client(base_url=self.base_url, timeout=0.5) as client:
                res = client.get("/api/version")
                self._cached_connected = (res.status_code == 200)
                if self._cached_connected:
                    self._cached_version = res.json().get("version")
                else:
                    self._cached_version = None
                self._last_check_time = now
                return self._cached_connected
        except Exception:
            self._cached_connected = False
            self._cached_version = None
            self._last_check_time = now
            return False

    def get_version(self) -> Optional[str]:
        """Fetch Ollama server version."""
        if not self.is_connected():
            return None
        return self._cached_version

    def list_models(self) -> List[Dict[str, Any]]:
        """Retrieve list of locally installed models."""
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                res = client.get("/api/tags")
                if res.status_code == 200:
                    return res.json().get("models", [])
        except Exception:
            pass
        return []

    def get_model_info(self, model_name: str, max_cache_age: float = 30.0) -> Dict[str, Any]:
        """Fetch model metadata and capabilities via /api/show."""
        import time
        if not hasattr(self, "_model_info_cache"):
            self._model_info_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}

        now = time.time()
        if model_name in self._model_info_cache:
            data, ts = self._model_info_cache[model_name]
            if now - ts < max_cache_age:
                return data

        try:
            with httpx.Client(base_url=self.base_url, timeout=3.0) as client:
                res = client.post("/api/show", json={"name": model_name})
                if res.status_code == 200:
                    info = res.json()
                    self._model_info_cache[model_name] = (info, now)
                    return info
        except Exception:
            pass
        return {}

    def get_model_features(self, model_name: str) -> List[str]:
        """Extract user-facing capabilities for a model (Tools, Vision, Reasoning)."""
        info = self.get_model_info(model_name)
        caps = info.get("capabilities", [])
        features: List[str] = []

        if "tools" in caps:
            features.append("Tools")
        if "vision" in caps or "clip" in str(info.get("projector_info", "")).lower():
            features.append("Vision")
        if "thinking" in caps:
            features.append("Reasoning")
        if "audio" in caps:
            features.append("Audio")

        if not features:
            lower = model_name.lower()
            if any(k in lower for k in ("gemma", "llama", "qwen", "mistral")):
                features.append("Tools")
            if "vision" in lower or "llava" in lower:
                features.append("Vision")
            if any(k in lower for k in ("r1", "qwq", "thinking")):
                features.append("Reasoning")

        return features or ["Text Generation"]

    def get_model_context_length(self, model_name: str, default: int = 8192) -> int:
        """Fetch model's defined context limit in tokens."""
        info = self.get_model_info(model_name)
        params = info.get("parameters", "")
        if "num_ctx" in params:
            for line in params.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0] == "num_ctx":
                    try:
                        return int(parts[1])
                    except ValueError:
                        pass

        model_info = info.get("model_info", {})
        for k, v in model_info.items():
            if k.endswith(".context_length") and isinstance(v, int):
                # If architecture length is very large, cap standard local window to 32768
                return min(v, 32768) if v > 32768 else v
        return default

    def get_model_architecture_info(self, model_name: str) -> Dict[str, Any]:
        """Extract model architectural parameters (layers, kv_heads, head_dim, context_length) from /api/show."""
        info = self.get_model_info(model_name)
        model_info = info.get("model_info", {})

        # 1. Layers (block_count)
        layers: Optional[int] = None
        for k, v in model_info.items():
            if k.endswith(".block_count") and isinstance(v, int) and "vision" not in k:
                layers = v
                break

        # 2. KV Heads (head_count_kv or head_count)
        kv_heads: Optional[Union[int, List[int]]] = None
        for k, v in model_info.items():
            if k.endswith(".attention.head_count_kv") and "vision" not in k:
                kv_heads = v
                break
        if kv_heads is None:
            for k, v in model_info.items():
                if k.endswith(".attention.head_count") and "vision" not in k and isinstance(v, int):
                    kv_heads = v
                    break

        # 3. Head Dim (key_length or embedding_length // head_count)
        head_dim: Optional[int] = None
        for k, v in model_info.items():
            if (k.endswith(".attention.key_length") or k.endswith(".attention.head_dimension")) and isinstance(v, int):
                head_dim = v
                break
        if head_dim is None:
            emb_len = None
            head_cnt = None
            for k, v in model_info.items():
                if k.endswith(".embedding_length") and isinstance(v, int) and "vision" not in k:
                    emb_len = v
                if k.endswith(".attention.head_count") and isinstance(v, int) and "vision" not in k:
                    head_cnt = v
            if emb_len and head_cnt and head_cnt > 0:
                head_dim = emb_len // head_cnt

        ctx_len = self.get_model_context_length(model_name, default=8192)

        # 4. Sliding Window Attention (SWA) parameters (e.g. Gemma, Mistral)
        sliding_window: Optional[int] = None
        swa_pattern: Optional[List[bool]] = None
        head_dim_swa: Optional[int] = None

        for k, v in model_info.items():
            if k.endswith(".attention.sliding_window") and isinstance(v, int):
                sliding_window = v
            elif k.endswith(".attention.sliding_window_pattern") and isinstance(v, list):
                swa_pattern = [bool(x) for x in v]
            elif k.endswith(".attention.key_length_swa") and isinstance(v, int):
                head_dim_swa = v

        return {
            "layers": layers,
            "kv_heads": kv_heads,
            "head_dim": head_dim,
            "context_length": ctx_len,
            "sliding_window": sliding_window,
            "swa_pattern": swa_pattern,
            "head_dim_swa": head_dim_swa,
        }

    def chat_turn(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        num_ctx: Optional[int] = None,
        stats_out: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Single chat turn supporting native tool calls and telemetry."""
        url = f"{self.base_url}/api/chat"
        opts: Dict[str, Any] = {"temperature": temperature}
        if num_ctx:
            opts["num_ctx"] = num_ctx

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": opts,
        }
        if tools:
            payload["tools"] = tools

        client_timeout = getattr(self, "timeout", 180.0) or 180.0
        with httpx.Client(timeout=httpx.Timeout(client_timeout, connect=15.0)) as client:
            res = client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            if stats_out is not None:
                stats_out.update({
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "eval_count": data.get("eval_count", 0),
                    "eval_duration": data.get("eval_duration", 0),
                    "total_duration": data.get("total_duration", 0),
                    "prompt_eval_duration": data.get("prompt_eval_duration", 0),
                })
            msg = data.get("message", {})
            if tools and not msg.get("tool_calls") and msg.get("content"):
                from locallm.core.tools import extract_fallback_tool_calls
                tool_names = {t.get("function", {}).get("name") for t in tools if isinstance(t, dict)}
                recovered = extract_fallback_tool_calls(msg.get("content", ""), tool_names)
                if recovered:
                    msg["tool_calls"] = recovered
            return msg

    def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        num_ctx: Optional[int] = None,
        stats_out: Optional[Dict[str, Any]] = None,
    ) -> Generator[str, None, None]:
        """Stream chat tokens from Ollama with optional telemetry collection."""
        url = f"{self.base_url}/api/chat"
        opts: Dict[str, Any] = {"temperature": temperature}
        if num_ctx:
            opts["num_ctx"] = num_ctx

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": opts,
        }

        with httpx.Client(timeout=None) as client:
            with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    msg = data.get("message", {})
                    token = msg.get("content", "")
                    if token:
                        yield token
                    if data.get("done", False):
                        if stats_out is not None:
                            stats_out.update({
                                "prompt_eval_count": data.get("prompt_eval_count", 0),
                                "eval_count": data.get("eval_count", 0),
                                "eval_duration": data.get("eval_duration", 0),
                                "total_duration": data.get("total_duration", 0),
                                "prompt_eval_duration": data.get("prompt_eval_duration", 0),
                            })
                        break

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        """Complete a single turn chat request without streaming."""
        tokens = list(self.chat_stream(model, messages, temperature))
        return "".join(tokens)

    def pull_model_stream(self, model_name: str) -> Generator[Dict[str, Any], None, None]:
        """Stream pull progress for a model."""
        url = f"{self.base_url}/api/pull"
        payload = {"name": model_name, "stream": True}

        with httpx.Client(timeout=None) as client:
            with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    yield json.loads(line)

    def get_loaded_models(self) -> List[str]:
        """Fetch list of active models currently loaded in memory/VRAM via /api/ps."""
        try:
            with httpx.Client(base_url=self.base_url, timeout=1.5) as client:
                res = client.get("/api/ps")
                if res.status_code == 200:
                    models = res.json().get("models", [])
                    result: List[str] = []
                    for m in models:
                        name = m.get("name") or m.get("model")
                        if name and name not in result:
                            result.append(name)
                    return result
        except Exception:
            pass
        return []

    def unload_model(self, model_name: str) -> bool:
        """Eject a specific model from VRAM immediately using keep_alive: 0."""
        if not model_name:
            return False
        try:
            with httpx.Client(base_url=self.base_url, timeout=2.0) as client:
                res = client.post("/api/generate", json={"model": model_name, "keep_alive": 0})
                return res.status_code == 200
        except Exception:
            return False

    def unload_all_models(self, fallback_model: Optional[str] = None) -> int:
        """Unload all active models currently occupying VRAM.

        Args:
            fallback_model: Optional default model name to unload if /api/ps is empty.

        Returns:
            int: Number of models successfully signaled to unload.
        """
        if not self.is_connected(max_cache_age=1.0):
            return 0

        loaded = self.get_loaded_models()
        if not loaded and fallback_model and fallback_model.lower() != "auto":
            loaded = [fallback_model]

        unloaded_count = 0
        for model in loaded:
            if self.unload_model(model):
                unloaded_count += 1
        return unloaded_count

    def delete_model(self, model_name: str) -> Tuple[bool, str]:
        """Delete a model from local Ollama storage and unload from memory."""
        clean_name = model_name.strip()
        if not clean_name:
            return False, "Model name cannot be empty."

        try:
            # First unload from VRAM if loaded
            self.unload_model(clean_name)
            with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
                res = client.request("DELETE", "/api/delete", json={"name": clean_name})
                if res.status_code == 200:
                    return True, f"Model '{clean_name}' deleted successfully."
                elif res.status_code == 404:
                    return False, f"Model '{clean_name}' not found on Ollama server."
                else:
                    return False, f"Failed to delete model '{clean_name}': {res.text}"
        except Exception as exc:
            return False, f"Network/server error deleting model '{clean_name}': {exc}"

