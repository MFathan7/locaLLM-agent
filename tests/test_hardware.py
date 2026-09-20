"""Unit tests for hardware and VRAM sizing calculation."""

import unittest
from unittest.mock import patch
from locallm.core.hardware import GPUInfo, check_vram_compatibility, get_system_resources


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


if __name__ == "__main__":
    unittest.main()
