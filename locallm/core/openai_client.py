"""OpenAI-compatible client for custom inference platforms (vLLM, LocalAI, etc.)."""

import json
import time
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
import httpx
from openai import OpenAI

from locallm.config import LocaLLMConfig, get_custom_platform
from locallm.core.ollama_client import OllamaClient


class OpenAIClient:
    """Synchronous client for OpenAI-compatible local and remote inference backends."""

    def __init__(
        self,
        api_base: str = "http://127.0.0.1:8000/v1",
        api_key: str = "",
        timeout: float = 60.0,
    ):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key.strip() or "not-needed"
        self.timeout = timeout
        self._cached_connected: Optional[bool] = None
        self._last_check_time: float = 0.0

        self.client = OpenAI(
            base_url=self.api_base,
            api_key=self.api_key,
            timeout=self.timeout,
        )

    def is_connected(self, max_cache_age: float = 5.0) -> bool:
        """Check if the target OpenAI-compatible endpoint is reachable."""
        now = time.time()
        if self._cached_connected is not None and (now - self._last_check_time < max_cache_age):
            return self._cached_connected

        try:
            # Quick probe using httpx to avoid long timeouts
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key != "not-needed" else {}
            models_url = f"{self.api_base}/models"
            with httpx.Client(timeout=1.5, headers=headers) as probe:
                res = probe.get(models_url)
                self._cached_connected = (res.status_code in (200, 401, 403))
                self._last_check_time = now
                return self._cached_connected
        except Exception:
            self._cached_connected = False
            self._last_check_time = now
            return False

    def get_version(self) -> Optional[str]:
        """Return platform version or indicator if connected."""
        if not self.is_connected():
            return None
        return "OpenAI-API"

    def list_models(self) -> List[Dict[str, Any]]:
        """Retrieve list of available models from the platform endpoint."""
        try:
            response = self.client.models.list()
            models: List[Dict[str, Any]] = []
            for m in response.data:
                models.append({
                    "name": m.id,
                    "id": m.id,
                    "owned_by": getattr(m, "owned_by", "custom"),
                    "created": getattr(m, "created", 0),
                })
            return models
        except Exception:
            return []

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Fetch model metadata if supported by endpoint."""
        try:
            m = self.client.models.retrieve(model_name)
            return {"name": m.id, "owned_by": getattr(m, "owned_by", "")}
        except Exception:
            return {"name": model_name}

    def get_model_features(self, model_name: str) -> List[str]:
        """Extract user-facing capabilities for a model."""
        features: List[str] = ["Tools"]
        lower = model_name.lower()

        if any(k in lower for k in ("vision", "vl", "4o", "llava", "omni", "multimodal")):
            features.append("Vision")
        if any(k in lower for k in ("r1", "qwq", "reasoner", "o1", "o3", "thinking")):
            features.append("Reasoning")

        return features

    def get_model_context_length(self, model_name: str, default: int = 8192) -> int:
        """Return context length for model."""
        return default

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format messages for OpenAI API, including multimodal image support."""
        converted: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            images = msg.get("images", [])

            if images and role == "user":
                parts: List[Dict[str, Any]] = [{"type": "text", "text": str(content)}]
                for img in images:
                    url = img if img.startswith(("http://", "https://", "data:")) else f"data:image/jpeg;base64,{img}"
                    parts.append({"type": "image_url", "image_url": {"url": url}})
                converted.append({"role": role, "content": parts})
            elif role == "tool":
                converted.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", "tool_call_1"),
                    "content": str(content),
                })
            elif role == "assistant" and msg.get("tool_calls"):
                converted.append({
                    "role": "assistant",
                    "content": str(content) if content else None,
                    "tool_calls": msg["tool_calls"],
                })
            else:
                converted.append({"role": role, "content": str(content)})
        return converted

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
        formatted_messages = self._convert_messages(messages)
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": formatted_messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools

        start_time = time.time()
        try:
            response = self.client.chat.completions.create(**kwargs)
            duration_ns = int((time.time() - start_time) * 1e9)

            choice = response.choices[0]
            msg = choice.message

            result: Dict[str, Any] = {
                "role": "assistant",
                "content": msg.content or "",
            }

            if msg.tool_calls:
                tool_calls_list = []
                for tc in msg.tool_calls:
                    tool_calls_list.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    })
                result["tool_calls"] = tool_calls_list
            elif tools and result.get("content"):
                from locallm.core.tools import extract_fallback_tool_calls
                tool_names = {t.get("function", {}).get("name") for t in tools if isinstance(t, dict)}
                fallback_calls = extract_fallback_tool_calls(result.get("content", ""), tool_names)
                if fallback_calls:
                    result["tool_calls"] = fallback_calls

            if stats_out is not None and response.usage:
                stats_out.update({
                    "prompt_eval_count": response.usage.prompt_tokens,
                    "eval_count": response.usage.completion_tokens,
                    "eval_duration": duration_ns,
                    "total_duration": duration_ns,
                    "prompt_eval_duration": 0,
                })
            elif stats_out is not None:
                token_est = len(result["content"]) // 4
                stats_out.update({
                    "prompt_eval_count": 0,
                    "eval_count": token_est,
                    "eval_duration": duration_ns,
                    "total_duration": duration_ns,
                })

            return result
        except Exception as exc:
            # If tool calling failed (e.g. backend doesn't support tools), retry without tools
            if tools:
                kwargs.pop("tools", None)
                response = self.client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                return {"role": "assistant", "content": choice.message.content or ""}
            raise exc

    def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        num_ctx: Optional[int] = None,
        stats_out: Optional[Dict[str, Any]] = None,
    ) -> Generator[str, None, None]:
        """Stream chat tokens from OpenAI-compatible platform."""
        formatted_messages = self._convert_messages(messages)
        start_time = time.time()
        eval_count = 0

        stream = self.client.chat.completions.create(
            model=model,
            messages=formatted_messages,
            temperature=temperature,
            stream=True,
        )

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = delta.content or ""
            if content:
                eval_count += max(1, len(content) // 4)
                yield content

        duration_ns = int((time.time() - start_time) * 1e9)
        if stats_out is not None:
            stats_out.update({
                "prompt_eval_count": 0,
                "eval_count": eval_count,
                "eval_duration": duration_ns,
                "total_duration": duration_ns,
                "prompt_eval_duration": 0,
            })

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
    ) -> str:
        """Complete a single turn chat request without streaming."""
        tokens = list(self.chat_stream(model, messages, temperature))
        return "".join(tokens)

    def unload_model(self, model_name: str) -> bool:
        """No-op for standard OpenAI endpoints."""
        return True

    def unload_all_models(self, fallback_model: Optional[str] = None) -> int:
        """No-op for standard OpenAI endpoints."""
        return 0

    def delete_model(self, model_name: str) -> Tuple[bool, str]:
        """Delete a model from the OpenAI-compatible platform endpoint if supported."""
        clean_name = model_name.strip()
        if not clean_name:
            return False, "Model name cannot be empty."

        try:
            res = self.client.models.delete(clean_name)
            deleted = getattr(res, "deleted", True)
            if deleted:
                return True, f"Model '{clean_name}' deleted successfully."
            return False, f"Endpoint responded without confirming deletion: {res}"
        except Exception as exc:
            # Fallback direct HTTP DELETE request if SDK method fails or backend requires custom handling
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key != "not-needed" else {}
                url = f"{self.api_base}/models/{clean_name}"
                with httpx.Client(timeout=10.0, headers=headers) as http_client:
                    r = http_client.delete(url)
                    if r.status_code in (200, 204):
                        return True, f"Model '{clean_name}' deleted successfully."
                    elif r.status_code == 405:
                        return False, f"Platform at '{self.api_base}' does not support deleting models (Method Not Allowed)."
                    elif r.status_code == 404:
                        return False, f"Model '{clean_name}' not found on platform."
                    else:
                        return False, f"Platform failed to delete model '{clean_name}': {r.text or r.status_code}"
            except Exception:
                return False, f"Platform does not support model deletion: {exc}"


def get_inference_client(config: LocaLLMConfig) -> Union[OllamaClient, OpenAIClient]:
    """Factory to instantiate the appropriate inference client for the active backend."""
    active = config.active_backend.strip().lower()
    if active == "ollama":
        return OllamaClient(base_url=config.ollama_host)

    custom_platform = get_custom_platform(config, active)
    if custom_platform:
        return OpenAIClient(
            api_base=custom_platform.api_base,
            api_key=custom_platform.api_key,
        )

    # Fallback to Ollama
    return OllamaClient(base_url=config.ollama_host)
