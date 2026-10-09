"""Unit tests for Workspace-Scoped Auto-Memory and Toggle Management."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from locallm.core.workspace import (
    create_workspace,
    get_workspace_path,
    load_workspace_context,
)
from locallm.core.workspace_memory import (
    MAX_WORKSPACE_FACTS,
    WorkspaceMemoryManager,
)
from locallm.core.auto_memory import (
    _extract_worker,
    _is_trivial_turn,
)


class TestWorkspaceMemoryManager(unittest.TestCase):
    """Test suite for WorkspaceMemoryManager."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mock_workspaces_dir = Path(self.temp_dir.name)
        self.patcher = patch(
            "locallm.core.workspace.get_workspaces_dir",
            return_value=self.mock_workspaces_dir,
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_workspace_isolation(self):
        """Facts stored in Workspace A must not leak into Workspace B."""
        ws_a = "peternakan"
        ws_b = "coding_project"

        create_workspace(ws_a)
        create_workspace(ws_b)

        mgr_a = WorkspaceMemoryManager(ws_a)
        mgr_b = WorkspaceMemoryManager(ws_b)

        mgr_a.set_fact("beli_ayam", "Beli 50 ekor ayam pada 15 September")
        mgr_b.set_fact("database", "Menggunakan PostgreSQL port 5432")

        facts_a = mgr_a.list_facts()
        facts_b = mgr_b.list_facts()

        self.assertIn("beli_ayam", facts_a)
        self.assertNotIn("database", facts_a)

        self.assertIn("database", facts_b)
        self.assertNotIn("beli_ayam", facts_b)

    def test_auto_memory_toggle(self):
        """Toggle status should be persisted in workspace.json and respected."""
        ws_name = "test_toggle_ws"
        create_workspace(ws_name, auto_memory=True)

        mgr = WorkspaceMemoryManager(ws_name)
        self.assertTrue(mgr.is_auto_memory_enabled())

        mgr.set_fact("event", "Peluncuran website tanggal 1 Oktober")
        context_enabled = mgr.build_workspace_memory_context()
        self.assertIn("Peluncuran website tanggal 1 Oktober", context_enabled)

        # Disable toggle
        mgr.set_auto_memory_enabled(False)
        self.assertFalse(mgr.is_auto_memory_enabled())

        # When disabled, context injection returns empty string
        context_disabled = mgr.build_workspace_memory_context()
        self.assertEqual(context_disabled, "")

        # Re-enable toggle
        mgr.set_auto_memory_enabled(True)
        self.assertTrue(mgr.is_auto_memory_enabled())
        self.assertIn("Peluncuran website tanggal 1 Oktober", mgr.build_workspace_memory_context())

    def test_delete_and_clear_facts(self):
        """Deleting individual facts and clearing all memory."""
        ws_name = "facts_ws"
        create_workspace(ws_name)
        mgr = WorkspaceMemoryManager(ws_name)

        mgr.set_fact("fact1", "Statement 1")
        mgr.set_fact("fact2", "Statement 2")
        self.assertEqual(len(mgr.list_facts()), 2)

        # Delete fact1
        self.assertTrue(mgr.delete_fact("fact1"))
        self.assertNotIn("fact1", mgr.list_facts())
        self.assertIn("fact2", mgr.list_facts())

        # Clear memory
        self.assertTrue(mgr.clear_memory())
        self.assertEqual(mgr.list_facts(), {})

    def test_max_facts_quota(self):
        """Store more than MAX_WORKSPACE_FACTS to ensure quota capping works."""
        ws_name = "quota_ws"
        create_workspace(ws_name)
        mgr = WorkspaceMemoryManager(ws_name)

        for i in range(MAX_WORKSPACE_FACTS + 10):
            mgr.set_fact(f"key_{i}", f"Value {i}")

        facts = mgr.list_facts()
        self.assertLessEqual(len(facts), MAX_WORKSPACE_FACTS)
        self.assertIn(f"key_{MAX_WORKSPACE_FACTS + 9}", facts)

    def test_corruption_fallback(self):
        """Ensure corrupted JSON is safely handled without raising uncaught exceptions."""
        ws_name = "corrupt_ws"
        create_workspace(ws_name)
        mgr = WorkspaceMemoryManager(ws_name)

        # Write corrupted JSON
        mgr.memory_file.write_text("{invalid_json: true,", encoding="utf-8")
        data = mgr.load()
        self.assertEqual(data, {"facts": {}})

    def test_extract_worker_respects_toggle(self):
        """Async extraction worker must skip execution if auto-memory is disabled."""
        ws_name = "worker_ws"
        create_workspace(ws_name, auto_memory=False)

        mock_client = MagicMock()
        _extract_worker(
            workspace_name=ws_name,
            client=mock_client,
            model="test_model",
            user_prompt="Kemarin saya beli 20 kambing",
            assistant_response="Baik, tercatat bahwa Anda membeli 20 kambing.",
        )

        # Client chat should never have been invoked because auto_memory is disabled
        mock_client.chat.assert_not_called()

    def test_trivial_turn_filtering(self):
        """Empty, whitespace, or system error turns should be filtered out structurally."""
        self.assertTrue(_is_trivial_turn("", "Halo! Ada yang bisa saya bantu?"))
        self.assertTrue(_is_trivial_turn("   ", "Siap."))
        self.assertTrue(_is_trivial_turn("hello", ""))
        self.assertTrue(_is_trivial_turn("test", "[System Error: backend offline]"))
        self.assertFalse(_is_trivial_turn(
            "Saya baru saja membeli 50 ekor sapi limousin pada tanggal 12 Agustus",
            "Selamat atas pembelian 50 ekor sapi limousin Anda!"
        ))
        self.assertFalse(_is_trivial_turn(
            "We deployed v2.1 to production server today",
            "Deployment noted."
        ))


if __name__ == "__main__":
    unittest.main()
