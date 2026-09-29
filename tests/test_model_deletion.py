"""Unit tests for general model deletion across Ollama and OpenAI-compatible platforms."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from locallm.config import CustomPlatformConfig, LocaLLMConfig, save_config
from locallm.core.ollama_client import OllamaClient
from locallm.core.openai_client import OpenAIClient
from locallm.modules.models_manager import _delete_model_wizard, _handle_deleted_model_fallback


class TestOllamaModelDeletion(unittest.TestCase):
    """Test OllamaClient.delete_model logic and error handling."""

    def setUp(self):
        self.client = OllamaClient(base_url="http://127.0.0.1:11434")

    def test_delete_empty_name(self):
        ok, msg = self.client.delete_model("   ")
        self.assertFalse(ok)
        self.assertIn("cannot be empty", msg)

    @patch("locallm.core.ollama_client.OllamaClient.unload_model")
    @patch("httpx.Client.request")
    def test_delete_success(self, mock_request, mock_unload):
        mock_resp = MagicMock(status_code=200)
        mock_request.return_value = mock_resp

        ok, msg = self.client.delete_model("qwen2.5:7b")
        self.assertTrue(ok)
        self.assertIn("deleted successfully", msg)
        mock_unload.assert_called_once_with("qwen2.5:7b")
        mock_request.assert_called_once_with("DELETE", "/api/delete", json={"name": "qwen2.5:7b"})

    @patch("locallm.core.ollama_client.OllamaClient.unload_model")
    @patch("httpx.Client.request")
    def test_delete_not_found(self, mock_request, mock_unload):
        mock_resp = MagicMock(status_code=404)
        mock_request.return_value = mock_resp

        ok, msg = self.client.delete_model("nonexistent:latest")
        self.assertFalse(ok)
        self.assertIn("not found", msg)


class TestOpenAIModelDeletion(unittest.TestCase):
    """Test OpenAIClient.delete_model logic and fallback handling."""

    def setUp(self):
        self.client = OpenAIClient(api_base="http://localhost:8000/v1", api_key="")

    def test_delete_empty_name(self):
        ok, msg = self.client.delete_model("")
        self.assertFalse(ok)
        self.assertIn("cannot be empty", msg)

    def test_delete_sdk_success(self):
        mock_del_res = MagicMock(deleted=True)
        self.client.client.models.delete = MagicMock(return_value=mock_del_res)

        ok, msg = self.client.delete_model("meta-llama/Llama-3-8B")
        self.assertTrue(ok)
        self.assertIn("deleted successfully", msg)
        self.client.client.models.delete.assert_called_once_with("meta-llama/Llama-3-8B")

    @patch("httpx.Client.delete")
    def test_delete_http_fallback_405(self, mock_http_delete):
        # SDK fails
        self.client.client.models.delete = MagicMock(side_effect=Exception("SDK delete unsupported"))
        # HTTP returns 405 Method Not Allowed
        mock_resp = MagicMock(status_code=405)
        mock_http_delete.return_value = mock_resp

        ok, msg = self.client.delete_model("remote-model")
        self.assertFalse(ok)
        self.assertIn("does not support deleting models", msg)


class TestModelDeletionWizard(unittest.TestCase):
    """Test general _delete_model_wizard and active model fallback synchronization."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = Path(self.temp_dir.name) / "config.json"
        self.patcher = patch("locallm.config.get_config_file_path", return_value=self.config_file)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    @patch("questionary.text")
    @patch("questionary.confirm")
    @patch("questionary.select")
    def test_wizard_ollama_deletion_with_active_fallback(self, mock_select, mock_confirm, mock_text):
        config = LocaLLMConfig(
            active_backend="ollama",
            ollama_model="model-a:latest",
            default_model="model-a:latest",
        )
        save_config(config)

        mock_client = MagicMock()
        mock_client.list_models.side_effect = [
            [{"name": "model-a:latest"}, {"name": "model-b:latest"}],  # Initial listing
            [{"name": "model-b:latest"}],  # Remaining models after deletion
        ]
        mock_client.delete_model.return_value = (True, "Model 'model-a:latest' deleted successfully.")

        mock_select.return_value.ask.return_value = "model-a:latest"
        mock_confirm.return_value.ask.return_value = True
        mock_text.return_value.ask.return_value = ""

        _delete_model_wizard(mock_client, config, platform_name="ollama")

        mock_client.delete_model.assert_called_once_with("model-a:latest")
        # Active model must have fallen back to remaining model-b:latest
        self.assertEqual(config.ollama_model, "model-b:latest")
        self.assertEqual(config.default_model, "model-b:latest")

    @patch("questionary.text")
    @patch("questionary.confirm")
    @patch("questionary.select")
    def test_wizard_custom_platform_deletion_with_active_fallback(self, mock_select, mock_confirm, mock_text):
        vllm = CustomPlatformConfig(
            name="vLLM",
            api_base="http://127.0.0.1:8000/v1",
            default_model="custom-mod-1",
        )
        config = LocaLLMConfig(
            active_backend="vLLM",
            default_model="custom-mod-1",
            custom_platforms=[vllm],
        )
        save_config(config)

        mock_client = MagicMock()
        mock_client.list_models.side_effect = [
            [{"id": "custom-mod-1"}, {"id": "custom-mod-2"}],
            [{"id": "custom-mod-2"}],
        ]
        mock_client.delete_model.return_value = (True, "Model 'custom-mod-1' deleted successfully.")

        mock_select.return_value.ask.return_value = "custom-mod-1"
        mock_confirm.return_value.ask.return_value = True
        mock_text.return_value.ask.return_value = ""

        _delete_model_wizard(mock_client, config, platform_name="vLLM")

        mock_client.delete_model.assert_called_once_with("custom-mod-1")
        # Active platform default and global default must fallback to custom-mod-2
        self.assertEqual(vllm.default_model, "custom-mod-2")
        self.assertEqual(config.default_model, "custom-mod-2")

    @patch("questionary.confirm")
    @patch("questionary.select")
    def test_wizard_cancel_confirmation(self, mock_select, mock_confirm):
        config = LocaLLMConfig()
        mock_client = MagicMock()
        mock_client.list_models.return_value = [{"name": "model-x"}]

        mock_select.return_value.ask.return_value = "model-x"
        mock_confirm.return_value.ask.return_value = False

        _delete_model_wizard(mock_client, config, platform_name="ollama")

        mock_client.delete_model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
