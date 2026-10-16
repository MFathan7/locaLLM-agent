"""Playwright End-to-End verification script for LocaLLM Visual Agent Workflow Studio."""

import os
from pathlib import Path
import time
from playwright.sync_api import sync_playwright

def test_workflow_end_to_end():
    print("\n--- Starting Playwright End-to-End Workflow Execution Test ---")
    repo_root = Path(__file__).resolve().parent.parent

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            permissions=["notifications"],
            accept_downloads=True,
        )
        page = context.new_page()
        page.on("console", lambda msg: print(f"CONSOLE [{msg.type}]: {msg.text}") if "error" in msg.type or "warn" in msg.type else None)

        # Step 1: Open workflow studio
        target_url = "http://localhost:5173/?page=workflow"
        print(f"[1] Navigating to {target_url}...")
        page.goto(target_url, wait_until="networkidle", timeout=20000)
        page.wait_for_timeout(1000)

        # Step 2: Verify page loaded and workflow title
        header_text = page.locator("header").text_content()
        print(f"[2] Header loaded: {header_text[:80]}...")
        assert "Run Pipeline" in header_text or "Halt Flow" in header_text, "Run Pipeline button not found"

        # Step 3: Switch to Preset: Deep Tech Intelligence & Synthesis
        switcher_btn = page.locator("button[title='Switch or create workflow']").first
        assert switcher_btn.is_visible(), "Workflow switcher button not found"
        switcher_btn.click()
        page.wait_for_timeout(400)

        tech_preset_btn = page.locator("button:has-text('Deep Tech')").first
        assert tech_preset_btn.is_visible(), "Deep Tech preset not found in dropdown"
        tech_preset_btn.click()
        print("[3] Selected Preset: Deep Tech & Market Intelligence Report")
        page.wait_for_timeout(600)

        # Step 4: Verify nodes rendered on canvas
        workflow_nodes = page.locator(".workflow-node")
        node_count = workflow_nodes.count()
        print(f"[4] Verified {node_count} workflow nodes rendered on canvas.")
        assert node_count >= 5, f"Expected at least 5 nodes on canvas, found {node_count}"

        # Step 5: Test Execution and Live Telemetry
        run_btn = page.locator("button:has-text('Run Pipeline')").first
        assert run_btn.is_visible(), "Run Pipeline button is not visible"

        print("[5] Clicking 'Run Pipeline' and listening for execution stream...")
        run_btn.click()
        page.wait_for_timeout(1500)

        # Verify live execution log drawer appears
        drawer = page.locator("text=Live Agent Pipeline Execution Log").first
        assert drawer.is_visible(), "Execution Drawer is not visible during run"
        print("[6] Live Execution Drawer is visible and streaming.")

        # Step 6: Test switching to Scheduled System Audit
        print("[7] Testing preset switch to Scheduled System Audit...")
        # If running, stop first
        halt_btn = page.locator("button:has-text('Halt Flow')").first
        if halt_btn.is_visible():
            halt_btn.click()
            page.wait_for_timeout(800)

        switcher_btn = page.locator("button[title='Switch or create workflow']").first
        switcher_btn.click()
        page.wait_for_timeout(400)
        sched_preset_btn = page.locator("button:has-text('Scheduled System Audit')").first
        assert sched_preset_btn.is_visible(), "Scheduled System Audit preset not found in dropdown"
        sched_preset_btn.click()
        page.wait_for_timeout(600)

        sched_nodes = page.locator(".workflow-node")
        print(f"[8] Verified {sched_nodes.count()} nodes loaded for Scheduled System Audit.")
        assert sched_nodes.count() >= 4, "Expected at least 4 nodes for Scheduled System Audit"

        print("\n--- Playwright End-to-End Workflow Test PASSED! ---")
        browser.close()

if __name__ == "__main__":
    test_workflow_end_to_end()
