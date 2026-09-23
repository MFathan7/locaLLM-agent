"""Unit tests for the Workspace Management Engine and strict knowledge isolation."""

import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import zipfile

from locallm.core.workspace import (
    add_workspace_document,
    add_workspace_skill,
    create_workspace,
    delete_workspace,
    ensure_default_workspace,
    extract_selected_skills,
    get_workspace_agents_path,
    get_workspace_info,
    inspect_github_skills,
    install_skill_from_source,
    list_workspaces,
    load_workspace_context,
    parse_github_source,
    sanitize_workspace_content,
    update_workspace_instructions,
)


class TestWorkspaceEngine(unittest.TestCase):
    """Test suite for workspace lifecycle, directory structure, and strict isolation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspaces_root = Path(self.temp_dir.name)
        self.patcher = patch("locallm.core.workspace.get_workspaces_dir", return_value=self.workspaces_root)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_default_workspace_scaffolding(self):
        default_dir = ensure_default_workspace()
        self.assertTrue(default_dir.exists())
        self.assertTrue((default_dir / "knowledge").is_dir())
        self.assertTrue((default_dir / "skills").is_dir())
        self.assertTrue((default_dir / "sessions").is_dir())
        self.assertTrue((default_dir / "workspace.json").is_file())

    def test_create_workspace_success(self):
        ok, msg = create_workspace(
            "finance_bot",
            description="Financial stock analysis",
            custom_instructions="Focus on balance sheets",
        )
        self.assertTrue(ok)
        self.assertIn("created successfully", msg)

        ws_info = get_workspace_info("finance_bot")
        self.assertIsNotNone(ws_info)
        self.assertEqual(ws_info["name"], "finance_bot")
        self.assertEqual(ws_info["description"], "Financial stock analysis")
        self.assertEqual(ws_info["custom_instructions"], "Focus on balance sheets")

    def test_create_workspace_validation(self):
        # Empty name
        ok, msg = create_workspace("")
        self.assertFalse(ok)
        self.assertIn("empty", msg)

        # Invalid characters (spaces, special symbols)
        ok, msg = create_workspace("invalid name with spaces!")
        self.assertFalse(ok)
        self.assertIn("must contain only letters", msg)

        # Duplicate creation
        ok1, _ = create_workspace("my-project")
        self.assertTrue(ok1)
        ok2, msg2 = create_workspace("my-project")
        self.assertFalse(ok2)
        self.assertIn("already exists", msg2)

    def test_list_workspaces(self):
        ensure_default_workspace()
        create_workspace("alpha", description="Alpha project")
        create_workspace("beta", description="Beta project")

        workspaces = list_workspaces()
        names = [w["name"] for w in workspaces]
        self.assertIn("default", names)
        self.assertIn("alpha", names)
        self.assertIn("beta", names)

    def test_delete_workspace_constraints(self):
        ensure_default_workspace()
        create_workspace("project-x")

        # Cannot delete 'default'
        ok, msg = delete_workspace("default", active_workspace="project-x")
        self.assertFalse(ok)
        self.assertIn("cannot be deleted", msg)

        # Cannot delete currently active workspace
        ok, msg = delete_workspace("project-x", active_workspace="project-x")
        self.assertFalse(ok)
        self.assertIn("currently active", msg)

        # Can delete inactive custom workspace
        ok, msg = delete_workspace("project-x", active_workspace="default")
        self.assertTrue(ok)
        self.assertIn("deleted successfully", msg)
        self.assertIsNone(get_workspace_info("project-x"))

    def test_strict_knowledge_isolation(self):
        """Verify that knowledge from Workspace A does NOT leak or bleed into Workspace B or default."""
        ensure_default_workspace()
        create_workspace("workspace_a", custom_instructions="Instructions for A")
        create_workspace("workspace_b", custom_instructions="Instructions for B")

        ws_a_dir = self.workspaces_root / "workspace_a"
        ws_b_dir = self.workspaces_root / "workspace_b"
        default_dir = self.workspaces_root / "default"

        # Add secret file to workspace_a
        (ws_a_dir / "knowledge" / "secret_a.md").write_text(
            "CLASSIFIED_FINANCIAL_REVENUE_A = 999M", encoding="utf-8"
        )

        # Add secret file to workspace_b
        (ws_b_dir / "knowledge" / "secret_b.md").write_text(
            "ENGINEERING_BLUEPRINT_B = HYPERDRIVE_V2", encoding="utf-8"
        )

        # 1. Inspect Workspace A context
        context_a = load_workspace_context("workspace_a")
        self.assertIn("CLASSIFIED_FINANCIAL_REVENUE_A", context_a)
        self.assertIn("Instructions for A", context_a)
        # MUST NOT contain B's knowledge
        self.assertNotIn("ENGINEERING_BLUEPRINT_B", context_a)
        self.assertNotIn("Instructions for B", context_a)

        # 2. Inspect Workspace B context
        context_b = load_workspace_context("workspace_b")
        self.assertIn("ENGINEERING_BLUEPRINT_B", context_b)
        self.assertIn("Instructions for B", context_b)
        # MUST NOT contain A's knowledge
        self.assertNotIn("CLASSIFIED_FINANCIAL_REVENUE_A", context_b)
        self.assertNotIn("Instructions for A", context_b)

        # 3. Inspect Default Workspace context
        context_default = load_workspace_context("default")
        self.assertNotIn("CLASSIFIED_FINANCIAL_REVENUE_A", context_default)
        self.assertNotIn("ENGINEERING_BLUEPRINT_B", context_default)

    def test_recursive_skill_folder_discovery(self):
        """Verify that nested skill subfolders (e.g. skills/antislop/SKILL.md) are discovered automatically."""
        create_workspace("nested_agent")
        ws_dir = self.workspaces_root / "nested_agent"
        nested_skill_dir = ws_dir / "skills" / "antislop"
        nested_skill_dir.mkdir(parents=True, exist_ok=True)

        (nested_skill_dir / "SKILL.md").write_text(
            "# Anti-Slop Guidelines\nNever use generic fluff in output.", encoding="utf-8"
        )

        context = load_workspace_context("nested_agent")
        self.assertIn("--- Skill: antislop/SKILL.md ---", context)
        self.assertIn("Never use generic fluff in output", context)

        info = get_workspace_info("nested_agent")
        self.assertIsNotNone(info)
        self.assertIn("antislop/SKILL.md", info["skill_files"])

    def test_update_workspace_instructions(self):
        create_workspace("instruct_ws")
        ok, msg = update_workspace_instructions("instruct_ws", "Always respond in JSON")
        self.assertTrue(ok)
        self.assertIn("updated", msg)

        info = get_workspace_info("instruct_ws")
        self.assertEqual(info["custom_instructions"], "Always respond in JSON")

        # Context includes instructions
        context = load_workspace_context("instruct_ws")
        self.assertIn("Always respond in JSON", context)

        # Invalid workspace returns False
        ok_bad, _ = update_workspace_instructions("nonexistent", "test")
        self.assertFalse(ok_bad)

    def test_add_workspace_document(self):
        create_workspace("doc_ws")
        ok, msg = add_workspace_document("doc_ws", "api_faq", "# FAQ\nQuestion 1")
        self.assertTrue(ok)
        self.assertIn("api_faq.md", msg)

        # Verify file on disk
        doc_path = self.workspaces_root / "doc_ws" / "knowledge" / "api_faq.md"
        self.assertTrue(doc_path.exists())
        self.assertEqual(doc_path.read_text(encoding="utf-8"), "# FAQ\nQuestion 1")

        # Verify context load
        context = load_workspace_context("doc_ws")
        self.assertIn("# FAQ\nQuestion 1", context)

    def test_add_workspace_skill(self):
        create_workspace("skill_ws")
        ok, msg = add_workspace_skill("skill_ws", "code_review", "# Code Review Guidelines")
        self.assertTrue(ok)
        self.assertIn("code_review/SKILL.md", msg)

        # Verify file on disk
        skill_file = self.workspaces_root / "skill_ws" / "skills" / "code_review" / "SKILL.md"
        self.assertTrue(skill_file.exists())
        self.assertEqual(skill_file.read_text(encoding="utf-8"), "# Code Review Guidelines")

        context = load_workspace_context("skill_ws")
        self.assertIn("code_review/SKILL.md", context)
        self.assertIn("# Code Review Guidelines", context)

    def test_parse_github_source(self):
        # 1. Full URL with tree and subpath
        o, r, b, s = parse_github_source("https://github.com/owner/my-repo/tree/main/skills/antislop-code")
        self.assertEqual(o, "owner")
        self.assertEqual(r, "my-repo")
        self.assertEqual(b, "main")
        self.assertEqual(s, "skills/antislop-code")

        # 2. Simple URL
        o, r, b, s = parse_github_source("https://github.com/owner/simple-repo")
        self.assertEqual(o, "owner")
        self.assertEqual(r, "simple-repo")
        self.assertIsNone(b)
        self.assertIsNone(s)

        # 3. Shorthand owner/repo
        o, r, b, s = parse_github_source("owner/shorthand-repo")
        self.assertEqual(o, "owner")
        self.assertEqual(r, "shorthand-repo")

        # 4. Shorthand with subpath
        o, r, b, s = parse_github_source("owner/multi-skill-repo/skills/security")
        self.assertEqual(o, "owner")
        self.assertEqual(r, "multi-skill-repo")
        self.assertEqual(s, "skills/security")

    def test_selective_skill_extraction_and_bloat_filtering(self):
        """Verify that multi-skill repositories only extract chosen skills and strictly filter bloat."""
        create_workspace("clean_agent")

        # Create mock multi-skill zip archive in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            # Skill 1: antislop
            zf.writestr("anti-slop-main/skills/antislop/SKILL.md", "# Anti-Slop Core")
            # Skill 2: antislop-code
            zf.writestr("anti-slop-main/skills/antislop-code/SKILL.md", "# Anti-Slop Code Guidelines")
            # Skill 3: antislop-human
            zf.writestr("anti-slop-main/skills/antislop-human/SKILL.md", "# Anti-Slop Human Guidelines")

            # Repository bloat that MUST be filtered out
            zf.writestr("anti-slop-main/.git/config", "git config data")
            zf.writestr("anti-slop-main/.github/workflows/ci.yml", "name: CI")
            zf.writestr("anti-slop-main/tests/test_rules.py", "def test_something(): pass")
            zf.writestr("anti-slop-main/package.json", '{"name": "anti-slop"}')
            zf.writestr("anti-slop-main/logo.png", b"\x89PNG\r\n\x1a\n")

        zip_bytes = zip_buffer.getvalue()

        # 1. Extract ONLY 'antislop-code'
        ok, msg = extract_selected_skills("clean_agent", zip_bytes, selected_skills=["antislop-code"])
        self.assertTrue(ok)
        self.assertIn("1 file(s)", msg)

        skills_dir = self.workspaces_root / "clean_agent" / "skills"
        # The selected skill MUST exist
        self.assertTrue((skills_dir / "antislop-code" / "SKILL.md").exists())
        self.assertEqual(
            (skills_dir / "antislop-code" / "SKILL.md").read_text(encoding="utf-8"),
            "# Anti-Slop Code Guidelines",
        )

        # Other unselected skills MUST NOT exist
        self.assertFalse((skills_dir / "antislop").exists())
        self.assertFalse((skills_dir / "antislop-human").exists())

        # Bloat files MUST NOT exist
        self.assertFalse((skills_dir / ".git").exists())
        self.assertFalse((skills_dir / ".github").exists())
        self.assertFalse((skills_dir / "tests").exists())
        self.assertFalse((skills_dir / "package.json").exists())
        self.assertFalse((skills_dir / "logo.png").exists())

    def test_install_skill_from_source_multi_guard(self):
        """Verify that multi-skill repos are not accidentally bulk dumped without skill selection."""
        ensure_default_workspace()
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("repo-main/skills/skill-a/SKILL.md", "Skill A")
            zf.writestr("repo-main/skills/skill-b/SKILL.md", "Skill B")
        zip_bytes = zip_buffer.getvalue()

        # Mock inspect_github_skills to return the 2 skills
        with patch("locallm.core.workspace.inspect_github_skills") as mock_inspect:
            mock_inspect.return_value = (True, "Discovered 2 skill(s).", ["skill-a", "skill-b"], zip_bytes, None)

            # Call install without specifying skill
            ok, msg, available = install_skill_from_source("default", "owner/repo")
            self.assertFalse(ok)
            self.assertIn("Repository contains 2 skills", msg)
            self.assertIn("Specify which skill(s) to install using --skill", msg)
            self.assertEqual(available, ["skill-a", "skill-b"])

            # Call install with specific skill
            ok2, msg2, installed2 = install_skill_from_source("default", "owner/repo", selected_skills=["skill-b"])
            self.assertTrue(ok2)
            self.assertEqual(installed2, ["skill-b"])

    def test_sanitize_workspace_content_and_surrogate_paste(self):
        """Verify that pasted Windows UTF-16 surrogate pairs and lone surrogates do not crash with UnicodeEncodeError."""
        # 1. Test raw sanitizer
        raw_surrogates = "Line 1: \ud83d\ude00\nLine 2 lone surrogate: \ud800\nEnd."
        cleaned = sanitize_workspace_content(raw_surrogates)
        self.assertIn("Line 1:", cleaned)
        # Re-encoding to UTF-8 must NOT raise UnicodeEncodeError
        encoded_bytes = cleaned.encode("utf-8")
        self.assertIsInstance(encoded_bytes, bytes)

        # 2. Test writing document with surrogates into knowledge/
        create_workspace("surrogate_ws")
        ok, msg = add_workspace_document("surrogate_ws", "README.md", raw_surrogates)
        self.assertTrue(ok)
        self.assertIn("README.md", msg)

        doc_file = self.workspaces_root / "surrogate_ws" / "knowledge" / "README.md"
        self.assertTrue(doc_file.exists())
        file_content = doc_file.read_text(encoding="utf-8")
        self.assertIn("Line 1:", file_content)

        # 3. Test update instructions with surrogates
        ok_inst, msg_inst = update_workspace_instructions("surrogate_ws", "Instruction: \ud83d\ude80 \ud800")
        self.assertTrue(ok_inst)
        info = get_workspace_info("surrogate_ws")
        self.assertIn("Instruction:", info["custom_instructions"])

    def test_workspace_cli_add_knowledge_with_file(self) -> None:
        """Verify that CLI _handle_workspace_cli parses --file using Path without NameError."""
        import tempfile
        from locallm.cli import _handle_workspace_cli
        from locallm.config import LocaLLMConfig

        create_workspace("cli_ws")
        cfg = LocaLLMConfig(active_workspace="cli_ws")

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".md") as tmp:
            tmp.write("# Test Knowledge\nSample knowledge text from file.")
            tmp_path = tmp.name

        try:
            class MockArgs:
                ws_action = "add-knowledge"
                workspace = "cli_ws"
                title = "cli_doc.md"
                content = None
                file = tmp_path

            # Calling _handle_workspace_cli must not raise NameError: name 'Path' is not defined
            _handle_workspace_cli(MockArgs(), cfg)

            doc_path = self.workspaces_root / "cli_ws" / "knowledge" / "cli_doc.md"
            self.assertTrue(doc_path.exists())
            self.assertIn("Sample knowledge text", doc_path.read_text(encoding="utf-8"))
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_default_workspace_agents_scaffolding(self):
        default_dir = ensure_default_workspace()
        agents_file = default_dir / "AGENTS.md"
        self.assertTrue(agents_file.is_file())
        content = agents_file.read_text(encoding="utf-8")
        self.assertIn("Autonomous Execution Authority", content)
        self.assertIn("search_web", content)

    def test_create_workspace_scaffolds_agents_md(self):
        ok, _ = create_workspace(
            "dev_agent",
            description="Software development workspace",
            custom_instructions="Always write clean docstrings and types.",
        )
        self.assertTrue(ok)
        agents_path = get_workspace_agents_path("dev_agent")
        self.assertTrue(agents_path.is_file())
        content = agents_path.read_text(encoding="utf-8")
        self.assertIn("Autonomous Execution Authority", content)
        self.assertIn("Always write clean docstrings and types.", content)

    def test_load_workspace_context_with_agents_md(self):
        create_workspace("custom_ws")
        agents_path = get_workspace_agents_path("custom_ws")
        agents_path.write_text("# Custom Persona\nYou are a specialized cyber analyst.", encoding="utf-8")

        ctx = load_workspace_context("custom_ws")
        self.assertIn("[Persona & Cognitive Directives (Workspace: custom_ws)]", ctx)
        self.assertIn("specialized cyber analyst", ctx)


if __name__ == "__main__":
    unittest.main()


