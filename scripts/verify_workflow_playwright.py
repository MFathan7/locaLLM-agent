"""Playwright End-to-End verification script for LocaLLM Visual Agent Workflow Studio."""

import os
from pathlib import Path
import time
from playwright.sync_api import sync_playwright

def test_workflow_end_to_end():
    print("\n--- Starting Playwright End-to-End Workflow Execution Test ---")
    repo_root = Path(__file__).resolve().parent.parent
    target_quran_doc = repo_root / "docs" / "quran_surah_output.md"

    # Clean existing artifact if present to ensure fresh creation
    if target_quran_doc.exists():
        target_quran_doc.unlink()
        print(f"Cleaned previous file at {target_quran_doc}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            permissions=["notifications"],
            accept_downloads=True,
        )
        page = context.new_page()
        page.on("console", lambda msg: print(f"CONSOLE [{msg.type}]: {msg.text}") if "error" in msg.type or "warn" in msg.type else None)
        page.on("response", lambda res: print(f"RESP: {res.url} -> {res.status}") if "workflow" in res.url else None)

        # Step 1: Open workflow studio
        target_url = "http://localhost:5173/?page=workflow"
        print(f"Navigating to {target_url}...")
        page.goto(target_url, wait_until="networkidle", timeout=15000)

        # Step 2: Verify page loaded and workflow title
        header_text = page.locator("header").text_content()
        print(f"Header loaded: {header_text[:80]}...")
        assert "Run Pipeline" in header_text or "Halt Flow" in header_text, "Run Pipeline button not found"

        # Step 3: Switch to Preset: Auto Grab Al-Qur'an & Tafsir (equran.id API)
        switcher_btn = page.locator("button[title='Switch or create workflow']").first
        assert switcher_btn.is_visible(), "Workflow switcher button not found"
        switcher_btn.click()
        page.wait_for_timeout(350)

        quran_preset_btn = page.locator("button:has-text('Auto Grab Al-Qur')").first
        assert quran_preset_btn.is_visible(), "Auto Grab Al-Qur'an preset not found in dropdown"
        quran_preset_btn.click()
        print("Selected Preset: Auto Grab Al-Qur'an & Tafsir (equran.id API)")
        page.wait_for_timeout(600)

        # Step 4: Verify that the activity icons on the canvas are properly rendered
        workflow_nodes = page.locator(".workflow-node")
        node_count = workflow_nodes.count()
        print(f"Verified {node_count} workflow nodes rendered on canvas.")
        assert node_count >= 6, f"Expected at least 6 nodes on canvas, found {node_count}"

        # Step 5: Start execution and catch auto-download
        run_btn = page.locator("button:has-text('Run Pipeline')").first
        assert run_btn.is_visible(), "Run Pipeline button is not visible"

        print("Clicking 'Run Pipeline' and listening for auto-download...")

        download_captured = None
        try:
            with page.expect_download(timeout=35000) as download_info:
                run_btn.click()
                print("Run Pipeline clicked. Stepping through nodes and awaiting completion...")
                # Wait for Artifacts card in UI
                page.wait_for_selector("text=Generated Deliverables", timeout=35000)
            download_captured = download_info.value
            print(f"Captured auto-download event: {download_captured.suggested_filename}")
        except Exception as exc:
            print(f"Auto-download wait note: {exc}")

        # Step 6: Verify file on disk
        print(f"Checking disk location: {target_quran_doc}...")
        for _ in range(15):
            if target_quran_doc.exists():
                break
            time.sleep(0.5)

        assert target_quran_doc.exists(), f"File was NOT created on disk at {target_quran_doc}"
        content = target_quran_doc.read_text(encoding="utf-8")
        assert "Al-Qur'an" in content or "Surat" in content, "Deliverable content does not contain Quran headers"
        print(f"File verified on disk ({len(content)} bytes):\n{content[:280]}...\n")

        # Step 7: Verify Execution Drawer details
        drawer = page.locator("text=Live Agent Pipeline Execution Log")
        assert drawer.is_visible(), "Execution Drawer is not visible"

        # Check for Artifact card in drawer
        artifact_card = page.locator("text=Generated Deliverables")
        assert artifact_card.is_visible(), "Artifacts Card in Execution Drawer is not visible"
        print("Artifact card is visible in Execution Drawer.")

        # Check disk path displayed
        disk_label = page.locator("text=Disk Location:").first
        assert disk_label.is_visible(), "Disk Location label is not visible in Execution Drawer"
        print(f"Disk location label verified: {disk_label.text_content()}")

        # Step 8: Test switching to Scheduled Audit & Human Approval Gate preset
        print("Testing preset switch to Scheduled System Audit & Human Approval Gate...")
        page.wait_for_timeout(400)
        switcher_btn = page.locator("button[title='Switch or create workflow']").first
        switcher_btn.click()
        page.wait_for_timeout(350)
        sched_btn = page.locator("button:has-text('Scheduled System Audit')").first
        assert sched_btn.is_visible(), "Scheduled Audit preset not found in dropdown"
        sched_btn.click()
        page.wait_for_timeout(500)

        sched_nodes_count = page.locator(".workflow-node").count()
        print(f"Successfully loaded Scheduled System Audit preset with {sched_nodes_count} nodes.")
        assert sched_nodes_count >= 6, "Scheduled audit preset nodes not properly rendered"

        browser.close()
        print("--- Playwright End-to-End Workflow Test Passed Successfully! ---\n")

if __name__ == "__main__":
    test_workflow_end_to_end()
