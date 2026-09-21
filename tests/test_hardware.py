"""Unit tests for hardware and VRAM sizing calculation."""

import unittest
from unittest.mock import MagicMock, patch
from locallm.core.hardware import (
    GPUInfo,
    calculate_vram_breakdown,
    check_vram_compatibility,
    get_system_resources,
)
from locallm.core.ollama_client import OllamaClient


class TestHardware(unittest.TestCase):
    """Test hardware inspection and VRAM safety thresholds."""

    @patch("locallm.core.hardware.get_gpu_info")
    def test_vram_compatibility_fits(self, mock_gpu):
        # 12 GB GPU with 10 GB free
        mock_gpu.return_value = GPUInfo(
            name="NVIDIA RTX Test",
            total_vram_mb=12288,
            free_vram_mb=10240,
            used_vram_mb=2048,
        )
        # 7 GB model
        size_7gb = int(7 * 1024 * 1024 * 1024)
        is_ok, msg = check_vram_compatibility(size_7gb)
        self.assertTrue(is_ok)
        self.assertIn("FIT", msg)

    @patch("locallm.core.hardware.get_gpu_info")
    def test_vram_compatibility_exceeds(self, mock_gpu):
        # 8 GB GPU with 4 GB free
        mock_gpu.return_value = GPUInfo(
            name="NVIDIA RTX Small",
            total_vram_mb=8192,
            free_vram_mb=4096,
            used_vram_mb=4096,
        )
        # 16 GB model
        size_16gb = int(16 * 1024 * 1024 * 1024)
        is_ok, msg = check_vram_compatibility(size_16gb)
        self.assertFalse(is_ok)
        self.assertIn("NOT FIT", msg)

    def test_system_resources_retrieval(self):
        resources = get_system_resources()
        self.assertGreater(resources.ram_total_gb, 0)
        self.assertGreater(resources.ram_available_gb, 0)

    def test_calculate_vram_breakdown_scalar_gqa(self):
        """Test standard GQA model VRAM sizing (e.g. Llama 3 8B)."""
        gpu = GPUInfo(
            name="RTX 3060",
            total_vram_mb=12288,
            free_vram_mb=11264,  # 11.0 GB Free
            used_vram_mb=1024,
        )
        # Model size: 4.68 GB (Q4_K_M)
        model_size = int(4.68 * (1024**3))
        res = calculate_vram_breakdown(
            model_size_bytes=model_size,
            context_tokens=8192,
            layers=28,
            kv_heads=4,
            head_dim=128,
            precision_bytes=2,
            cuda_overhead_gb=0.6,
            gpu_info=gpu,
        )
        # Bytes per token = 2 * 28 * 4 * 128 * 2 = 57,344 bytes
        self.assertEqual(res.bytes_per_token, 57344)
        # KV Cache for 8,192 tokens = 57,344 * 8192 = 469,762,048 bytes ~ 0.437 GB
        self.assertAlmostEqual(res.kv_cache_gb, 0.437, places=2)
        # Total VRAM = 4.68 + 0.437 + 0.6 = 5.717 GB
        self.assertAlmostEqual(res.total_vram_gb, 5.717, places=2)
        self.assertTrue(res.is_fit)
        self.assertEqual(res.status, "100% GPU")
        self.assertGreater(res.headroom_gb, 5.0)
        # Max context tokens: (11.0 - 4.68 - 0.6) * 1024^3 / 57344 ~ 107,105
        self.assertGreater(res.max_context_tokens, 100000)

    def test_calculate_vram_breakdown_list_heads(self):
        """Test per-block KV head list (e.g. hybrid / SWA models)."""
        gpu = GPUInfo(
            name="RTX 4090",
            total_vram_mb=24576,
            free_vram_mb=20480,
            used_vram_mb=4096,
        )
        model_size = int(6.0 * (1024**3))
        # 4 layers: 2 layers have 4 heads, 2 layers have 0 heads
        kv_heads_list = [4, 0, 4, 0]
        res = calculate_vram_breakdown(
            model_size_bytes=model_size,
            context_tokens=2048,
            layers=4,
            kv_heads=kv_heads_list,
            head_dim=128,
            precision_bytes=2,
            gpu_info=gpu,
        )
        # Total channels = (4 + 0 + 4 + 0) * 128 = 1024
        # Bytes per token = 2 * 1024 * 2 = 4096
        self.assertEqual(res.bytes_per_token, 4096)
        self.assertTrue(res.is_fit)

    def test_calculate_vram_breakdown_no_gpu(self):
        """Test CPU mode behavior when no GPU is detected."""
        model_size = int(5.0 * (1024**3))
        res = calculate_vram_breakdown(
            model_size_bytes=model_size,
            context_tokens=4096,
            gpu_info=None,
        )
        self.assertFalse(res.is_fit)
        self.assertEqual(res.status, "CPU MODE")
        self.assertEqual(res.max_context_tokens, 0)
        self.assertIn("No GPU detected", res.status_message)

    def test_calculate_vram_spillover(self):
        """Test spillover detection when model + KV exceeds usable VRAM."""
        gpu = GPUInfo(
            name="RTX 3050 4GB",
            total_vram_mb=4096,
            free_vram_mb=3072,  # 3.0 GB Free
            used_vram_mb=1024,
        )
        # 5 GB model
        model_size = int(5.0 * (1024**3))
        res = calculate_vram_breakdown(
            model_size_bytes=model_size,
            context_tokens=8192,
            gpu_info=gpu,
        )
        self.assertFalse(res.is_fit)
        self.assertEqual(res.status, "SPILLOVER")
        self.assertLess(res.headroom_gb, 0)
        self.assertEqual(res.max_context_tokens, 0)

    def test_ollama_client_get_model_architecture_info(self):
        """Test extraction of architectural metadata from Ollama /api/show response."""
        client = OllamaClient()
        mock_show = {
            "model_info": {
                "llama.block_count": 32,
                "llama.attention.head_count_kv": 8,
                "llama.attention.key_length": 128,
                "llama.context_length": 131072,
            },
            "parameters": "num_ctx 16384",
        }
        with patch.object(client, "get_model_info", return_value=mock_show):
            arch = client.get_model_architecture_info("test-llama:latest")
            self.assertEqual(arch["layers"], 32)
            self.assertEqual(arch["kv_heads"], 8)
            self.assertEqual(arch["head_dim"], 128)
            self.assertEqual(arch["context_length"], 16384)

    def test_calculate_vram_breakdown_sliding_window_attention(self):
        """Test Gemma/Mistral style Sliding Window Attention (SWA) VRAM capping."""
        gpu = GPUInfo(
            name="RTX 3060 12GB",
            total_vram_mb=12288,
            free_vram_mb=10645,  # 10.4 GB Free
            used_vram_mb=1643,
        )
        model_size = int(6.66 * (1024**3))  # Gemma 4 12B QAT
        # 5 SWA layers (window 1024, dim 256, 8 heads) + 1 Full Attention layer (dim 512, 1 head)
        kv_heads = [8, 8, 8, 8, 8, 1] * 8  # 48 layers total
        swa_pattern = [True, True, True, True, True, False] * 8

        res = calculate_vram_breakdown(
            model_size_bytes=model_size,
            context_tokens=65536,
            layers=48,
            kv_heads=kv_heads,
            head_dim=512,
            head_dim_swa=256,
            sliding_window=1024,
            swa_pattern=swa_pattern,
            precision_bytes=2,
            cuda_overhead_gb=0.6,
            gpu_info=gpu,
        )
        # SWA prevents 48 GB runaway: KV Cache is only ~1.31 GB
        self.assertAlmostEqual(res.kv_cache_gb, 1.312, places=2)
        # Total VRAM is ~8.57 GB (< 10 GB)
        self.assertLess(res.total_vram_gb, 9.0)
        self.assertTrue(res.is_fit)
        self.assertEqual(res.status, "100% GPU")
        self.assertGreater(res.headroom_gb, 1.5)
        # Max context tokens scales up to >150k
        self.assertGreater(res.max_context_tokens, 150000)


if __name__ == "__main__":
    unittest.main()
