"""Unit tests for Custom Platform (OpenAI-compatible) system and client."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from locallm.config import (
    CustomPlatformConfig,
    LocaLLMConfig,
    add_custom_platform,
    get_custom_platform,
    load_config,
    remove_custom_platform,
    save_config,
    switch_active_backend,
    update_custom_platform,
)
from locallm.core.openai_client import OpenAIClient, get_inference_client
from locallm.core.service_manager import get_all_services_status, is_custom_platform_reachable


class TestCustomPlatforms(unittest.TestCase):
    """Test suite for custom OpenAI-compatible platforms."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = Path(self.temp_dir.name) / "config.json"
        self.patcher = patch("locallm.config.get_config_file_path", return_value=self.config_file)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_custom_platform_config_crud(self):
        config = LocaLLMConfig()
        save_config(config)

        # Add platform
        vllm = CustomPlatformConfig(
            name="vLLM",
            api_base="http://127.0.0.1:8000/v1",
            api_key="secret-key",
            default_model="llama-3",
        )
        ok, msg = add_custom_platform(config, vllm)
        self.assertTrue(ok)
        self.assertIn("added successfully", msg)

        # Retrieve platform
        found = get_custom_platform(config, "vllm")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "vLLM")
        self.assertEqual(found.api_base, "http://127.0.0.1:8000/v1")
        self.assertEqual(found.api_key, "secret-key")

        # Duplicate addition rejection
        ok_dup, msg_dup = add_custom_platform(config, vllm)
        self.assertFalse(ok_dup)
        self.assertIn("already exists", msg_dup)

        # Reserved name rejection
        ok_res, msg_res = add_custom_platform(config, CustomPlatformConfig(name="ollama"))
        self.assertFalse(ok_res)
        self.assertIn("reserved", msg_res)

        # Update platform
        ok_up, msg_up = update_custom_platform(
            config,
            "vLLM",
            api_base="http://127.0.0.1:9000/v1",
            api_key="new-key",
        )
        self.assertTrue(ok_up)
        updated = get_custom_platform(config, "vLLM")
        self.assertEqual(updated.api_base, "http://127.0.0.1:9000/v1")
        self.assertEqual(updated.api_key, "new-key")

        # Remove platform while active and with platform-specific model selected
        config.active_backend = "vLLM"
        config.default_model = "llama-3"
        config.ollama_model = "gemma4:12b"
        save_config(config)
        with patch("locallm.core.ollama_client.OllamaClient.is_connected", return_value=False):
            ok_rem, msg_rem = remove_custom_platform(config, "vLLM")
        self.assertTrue(ok_rem)
        self.assertIsNone(get_custom_platform(config, "vLLM"))
        # Verify fallback to ollama AND that model is no longer the deleted platform's model
        self.assertEqual(config.active_backend, "ollama")
        self.assertEqual(config.default_model, "gemma4:12b")

    def test_switch_active_backend_and_model_sync(self):
        config = LocaLLMConfig(default_model="gemma4:12b", ollama_model="gemma4:12b")
        vllm = CustomPlatformConfig(
            name="vLLM",
            api_base="http://127.0.0.1:8000/v1",
            default_model="meta-llama-3-8b",
        )
        add_custom_platform(config, vllm)

        # Switch to vLLM: active model should become vLLM's model
        ok, msg = switch_active_backend(config, "vLLM")
        self.assertTrue(ok)
        self.assertEqual(config.active_backend, "vLLM")
        self.assertEqual(config.default_model, "meta-llama-3-8b")

        # Switch back to Ollama: active model should restore to Ollama's model
        ok2, msg2 = switch_active_backend(config, "ollama")
        self.assertTrue(ok2)
        self.assertEqual(config.active_backend, "ollama")
        self.assertEqual(config.default_model, "gemma4:12b")

    def test_legacy_lmstudio_migration(self):
        # Simulate legacy config with lmstudio_host and active_backend = lmstudio
        legacy_data = {
            "active_backend": "lmstudio",
            "lmstudio_host": "http://127.0.0.1:1234/v1",
            "ollama_host": "http://127.0.0.1:11434",
            "default_model": "test-model",
        }
        import json
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(legacy_data, f)

        loaded = load_config()
        self.assertEqual(loaded.active_backend, "ollama")
        self.assertFalse(hasattr(loaded, "lmstudio_host"))
        self.assertEqual(len(loaded.custom_platforms), 0)

    @patch("openai.resources.models.Models.list")
    def test_openai_client_list_models(self, mock_models_list):
        mock_model1 = MagicMock(id="meta-llama/Llama-3-8B-Instruct", owned_by="vllm", created=1700000000)
        mock_model2 = MagicMock(id="mistralai/Mistral-7B", owned_by="custom", created=1700000100)
        mock_models_list.return_value = MagicMock(data=[mock_model1, mock_model2])

        client = OpenAIClient(api_base="http://localhost:8000/v1", api_key="")
        models = client.list_models()
        self.assertEqual(len(models), 2)
        self.assertEqual(models[0]["id"], "meta-llama/Llama-3-8B-Instruct")
        self.assertEqual(models[0]["owned_by"], "vllm")
        self.assertEqual(models[1]["id"], "mistralai/Mistral-7B")

    def test_openai_client_features(self):
        client = OpenAIClient()
        caps1 = client.get_model_features("meta-llama/Llama-3-Vision-Instruct")
        self.assertIn("Vision", caps1)
        self.assertIn("Tools", caps1)

        caps2 = client.get_model_features("deepseek-r1-distill")
        self.assertIn("Reasoning", caps2)

    @patch("openai.resources.chat.completions.Completions.create")
    def test_openai_client_chat_turn(self, mock_create):
        mock_choice = MagicMock()
        mock_choice.message = MagicMock(content="Custom platform response", tool_calls=None)
        mock_response = MagicMock(
            choices=[mock_choice],
            usage=MagicMock(prompt_tokens=15, completion_tokens=25),
        )
        mock_create.return_value = mock_response

        client = OpenAIClient()
        stats: dict = {}
        res = client.chat_turn(
            model="llama-3",
            messages=[{"role": "user", "content": "Hello!"}],
            stats_out=stats,
        )
        self.assertEqual(res["content"], "Custom platform response")
        self.assertEqual(stats["prompt_eval_count"], 15)
        self.assertEqual(stats["eval_count"], 25)

    def test_get_inference_client_factory(self):
        config = LocaLLMConfig(active_backend="ollama")
        c1 = get_inference_client(config)
        self.assertEqual(c1.__class__.__name__, "OllamaClient")

        custom = CustomPlatformConfig(name="local-vllm", api_base="http://localhost:8000/v1")
        config.custom_platforms.append(custom)
        config.active_backend = "local-vllm"

        c2 = get_inference_client(config)
        self.assertEqual(c2.__class__.__name__, "OpenAIClient")
        self.assertEqual(c2.api_base, "http://localhost:8000/v1")

    @patch("httpx.Client.get")
    def test_is_custom_platform_reachable(self, mock_get):
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_get.return_value = mock_res

        self.assertTrue(is_custom_platform_reachable("http://127.0.0.1:8000/v1", max_cache_age=0.0))

        mock_get.side_effect = Exception("Connection refused")
        self.assertFalse(is_custom_platform_reachable("http://127.0.0.1:9999/v1", max_cache_age=0.0))

    @patch("locallm.core.service_manager.is_ollama_running", return_value=True)
    @patch("locallm.core.service_manager.is_custom_platform_reachable", return_value=True)
    def test_get_all_services_status(self, mock_custom_up, mock_ollama_up):
        platforms = [CustomPlatformConfig(name="vLLM", api_base="http://localhost:8000/v1")]
        statuses = get_all_services_status(custom_platforms=platforms)
        self.assertIn("Ollama", statuses)
        self.assertIn("vLLM", statuses)
        self.assertTrue(statuses["Ollama"])
        self.assertTrue(statuses["vLLM"])


if __name__ == "__main__":
    unittest.main()
