"""Unit tests for Live System Monitor HUD and extended hardware telemetry."""

import unittest
from unittest.mock import MagicMock, patch

from locallm.config import LocaLLMConfig
from locallm.core.hardware import GPUExtendedInfo, get_gpu_extended_info
from locallm.modules.monitor import (
    _check_exit_key,
    _make_progress_bar,
    build_monitor_renderable,
    run_live_monitor,
)


class TestLiveMonitor(unittest.TestCase):
    """Test suite for real-time live monitor HUD."""

    def test_make_progress_bar(self):
        # Zero total
        bar_zero = _make_progress_bar(0, 0, width=10)
        self.assertEqual(bar_zero, "[░░░░░░░░░░]")

        # Half filled
        bar_half = _make_progress_bar(5, 10, width=10)
        self.assertEqual(bar_half, "[█████░░░░░]")

        # Full filled
        bar_full = _make_progress_bar(10, 10, width=10)
        self.assertEqual(bar_full, "[██████████]")

    @patch("locallm.modules.monitor.get_gpu_extended_info")
    @patch("locallm.modules.monitor.psutil")
    def test_build_monitor_renderable_with_gpu(self, mock_psutil, mock_gpu):
        mock_gpu.return_value = GPUExtendedInfo(
            name="NVIDIA GeForce RTX 4070",
            total_vram_mb=12288,
            free_vram_mb=6144,
            used_vram_mb=6144,
            utilization_pct=45,
            temperature_c=58,
        )
        mock_mem = MagicMock()
        mock_mem.total = 32 * (1024**3)
        mock_mem.available = 16 * (1024**3)
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem
        mock_psutil.cpu_percent.return_value = 12.5
        mock_psutil.cpu_count.return_value = 16

        cfg = LocaLLMConfig()
        client = MagicMock()
        client.is_connected.return_value = True
        client.get_loaded_models.return_value = ["deepseek-r1:8b", "llama3.2:latest"]

        panel = build_monitor_renderable(cfg, client)
        self.assertIsNotNone(panel)
        self.assertIn("✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ   s ʏ s ᴛ ᴇ ᴍ   ᴍ ᴏ ɴ ɪ ᴛ ᴏ ʀ  ✦", str(panel.title))

    @patch("locallm.modules.monitor.get_gpu_extended_info", return_value=None)
    @patch("locallm.modules.monitor.psutil")
    def test_build_monitor_renderable_cpu_mode(self, mock_psutil, mock_gpu):
        mock_mem = MagicMock()
        mock_mem.total = 16 * (1024**3)
        mock_mem.available = 8 * (1024**3)
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem
        mock_psutil.cpu_percent.return_value = 5.0
        mock_psutil.cpu_count.return_value = 8

        cfg = LocaLLMConfig()
        client = MagicMock()
        client.is_connected.return_value = False
        client.get_loaded_models.return_value = []

        panel = build_monitor_renderable(cfg, client)
        self.assertIsNotNone(panel)

    @patch("locallm.modules.monitor.Live")
    @patch("locallm.modules.monitor.console")
    def test_run_live_monitor_max_iterations(self, mock_console, mock_live):
        cfg = LocaLLMConfig()
        client = MagicMock()
        client.is_connected.return_value = True
        client.get_loaded_models.return_value = []

        # Run with max_iterations=1 to ensure safe termination
        run_live_monitor(cfg, client, refresh_interval=0.2, max_iterations=1)
        mock_live.assert_called_once()

    @patch("locallm.core.hardware.shutil.which", return_value=None)
    def test_get_gpu_extended_info_no_nvidia_smi(self, mock_which):
        info = get_gpu_extended_info(force_refresh=True)
        self.assertIsNone(info)

    @patch("locallm.core.hardware.shutil.which", return_value="nvidia-smi")
    @patch("locallm.core.hardware.subprocess.run")
    def test_get_gpu_extended_info_success(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            stdout="NVIDIA RTX 4070, 12288, 6144, 6144, 30, 52\n"
        )
        info = get_gpu_extended_info(force_refresh=True)
        self.assertIsNotNone(info)
        self.assertEqual(info.name, "NVIDIA RTX 4070")
        self.assertEqual(info.total_vram_mb, 12288)
        self.assertEqual(info.free_vram_mb, 6144)
        self.assertEqual(info.used_vram_mb, 6144)
        self.assertEqual(info.utilization_pct, 30)
        self.assertEqual(info.temperature_c, 52)


if __name__ == "__main__":
    unittest.main()
