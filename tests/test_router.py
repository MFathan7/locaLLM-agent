"""Unit tests for the Intelligent Semantic Model Router."""

import unittest
from unittest.mock import MagicMock, patch

from locallm.config import LocaLLMConfig
from locallm.core.hardware import VRAMSizingResult
from locallm.core.router import (
    ModelRouteResult,
    TaskTier,
    TaskType,
    classify_prompt,
    is_match_negated,
    route_prompt,
)


class TestModelRouter(unittest.TestCase):
    """Test suite for prompt classification, candidate selection, sticky routing, and VRAM guard."""

    def setUp(self):
        self.config = LocaLLMConfig()
        self.config.default_model = "auto"
        self.config.context_window = 8192

    def test_classify_prompt_fast_chat(self):
        """Test simple greetings and quick factual queries."""
        task, tier, reason = classify_prompt("hello there!")
        self.assertEqual(task, TaskType.FAST_CHAT)
        self.assertEqual(tier, TaskTier.FAST)

        task2, tier2, _ = classify_prompt("halo apa kabar?")
        self.assertEqual(task2, TaskType.FAST_CHAT)
        self.assertEqual(tier2, TaskTier.FAST)

    def test_classify_prompt_coding(self):
        """Test detection of code syntax and development queries."""
        code_prompt = (
            "Here is my code:\n"
            "```python\n"
            "def calculate(n):\n"
            "    return n * 2\n"
            "```\n"
            "How do I refactor this?"
        )
        task, tier, _ = classify_prompt(code_prompt)
        self.assertEqual(task, TaskType.CODING)

        # Complex debugging with traceback elevates to DEEP_REASONING
        debug_prompt = "Why does this traceback happen? def main(): raise ValueError('null pointer')"
        task_debug, tier_debug, _ = classify_prompt(debug_prompt)
        self.assertEqual(task_debug, TaskType.CODING)
        self.assertEqual(tier_debug, TaskTier.DEEP_REASONING)

    def test_classify_prompt_deep_reasoning(self):
        """Test mathematical, causal, and architectural reasoning prompts."""
        reason_prompt = "Prove step-by-step why the time complexity of merge sort is O(N log N) in all cases."
        task, tier, _ = classify_prompt(reason_prompt)
        self.assertEqual(task, TaskType.REASONING)
        self.assertEqual(tier, TaskTier.DEEP_REASONING)

        arch_prompt = "Compare and contrast the trade-offs between event-driven and monolithic architectures."
        task_arch, tier_arch, _ = classify_prompt(arch_prompt)
        self.assertEqual(task_arch, TaskType.REASONING)
        self.assertEqual(tier_arch, TaskTier.DEEP_REASONING)

    def test_classify_prompt_tools_and_agent(self):
        """Test tool execution intent and agent task flag."""
        tool_prompt = "read file config.json and show the contents"
        task, tier, _ = classify_prompt(tool_prompt)
        self.assertEqual(task, TaskType.TOOLS)

        agent_task, agent_tier, _ = classify_prompt("clean up temp files", is_agent_task=True)
        self.assertEqual(agent_task, TaskType.TOOLS)
        self.assertEqual(agent_tier, TaskTier.DEEP_REASONING)

    def test_classify_prompt_file_creation_and_path(self):
        """Test structural filesystem paths and file creation intents."""
        prompt1 = "bisa gak kamu buatkan filenya di folder ini C:\\Users\\mfath\\Downloads\\Bot Signal"
        task1, tier1, _ = classify_prompt(prompt1)
        self.assertEqual(task1, TaskType.TOOLS)
        self.assertEqual(tier1, TaskTier.DEEP_REASONING)

        prompt2 = "can you create the files in /home/user/workspace/bot"
        task2, tier2, _ = classify_prompt(prompt2)
        self.assertEqual(task2, TaskType.TOOLS)
        self.assertEqual(tier2, TaskTier.DEEP_REASONING)

    def test_classify_prompt_multi_turn_context(self):
        """Test multi-turn context awareness preserving technical workflow across turns."""
        history = [
            {"role": "user", "content": "Buat architecture modular yang scalable"},
            {"role": "assistant", "content": "Berikut rancangannya:\n```python\nclass App: pass\n```\n├── config.py\n└── main.py"},
        ]
        # Very short prompt (2 words) that would otherwise be classified as FAST_CHAT
        followup_prompt = "buatkan filenya"
        task, tier, reason = classify_prompt(followup_prompt, history=history)
        self.assertEqual(task, TaskType.TOOLS)
        self.assertEqual(tier, TaskTier.DEEP_REASONING)
        self.assertIn("Technical follow-up", reason)

    def test_classify_prompt_vision(self):
        """Test visual input trigger."""
        task, tier, _ = classify_prompt("Describe this diagram", has_image=True)
        self.assertEqual(task, TaskType.VISION)
        self.assertEqual(tier, TaskTier.FAST)

    def test_route_prompt_sticky_routing_for_fast_chat(self):
        """Verify that fast chat does NOT swap active model unnecessarily (anti-thrashing)."""
        mock_client = MagicMock()
        mock_client.list_models.return_value = [
            {"name": "gemma4:12b", "size": 7 * 1024**3},
            {"name": "qwen2.5-coder:7b", "size": 4 * 1024**3},
            {"name": "deepseek-r1:8b", "size": 5 * 1024**3},
        ]
        # Currently loaded model in GPU
        mock_client.get_loaded_models.return_value = ["gemma4:12b"]
        mock_client.get_model_features.return_value = ["Text Generation"]

        route = route_prompt("hi there, how are you?", self.config, mock_client)
        self.assertEqual(route.selected_model, "gemma4:12b")
        self.assertFalse(route.is_swapped)
        self.assertIn("Direct fast execution on active model", route.reason)

    def test_route_prompt_dispatches_to_coder(self):
        """Verify that coding intent selects dedicated coder model if available."""
        mock_client = MagicMock()
        mock_client.list_models.return_value = [
            {"name": "gemma4:12b", "size": 7 * 1024**3},
            {"name": "qwen2.5-coder:7b", "size": 4 * 1024**3},
        ]
        mock_client.get_loaded_models.return_value = ["gemma4:12b"]
        mock_client.get_model_features.side_effect = lambda m: ["Tools"] if "coder" in m else []

        with patch("locallm.core.router.calculate_vram_breakdown") as mock_vram:
            mock_vram.return_value = VRAMSizingResult(
                model_weights_gb=4.0,
                kv_cache_gb=1.0,
                cuda_overhead_gb=0.6,
                total_vram_gb=5.6,
                usable_vram_gb=10.0,
                headroom_gb=4.4,
                is_fit=True,
                status="100% GPU",
                status_message="Fit",
                max_context_tokens=32768,
                context_tokens=8192,
                bytes_per_token=131072,
            )
            route = route_prompt(
                "Write a Python function to sort a list using quicksort:\ndef quicksort(arr):",
                self.config,
                mock_client,
            )
            self.assertEqual(route.selected_model, "qwen2.5-coder:7b")
            self.assertEqual(route.task_type, TaskType.CODING)
            self.assertTrue(route.is_swapped)

    def test_route_prompt_vram_safety_guard_prevents_oom(self):
        """Verify that router falls back to active model if candidate model exceeds VRAM."""
        mock_client = MagicMock()
        mock_client.list_models.return_value = [
            {"name": "gemma4:12b", "size": 7 * 1024**3},
            {"name": "deepseek-r1:70b", "size": 40 * 1024**3},
        ]
        mock_client.get_loaded_models.return_value = ["gemma4:12b"]
        mock_client.get_model_features.side_effect = lambda m: ["Reasoning"] if "r1" in m else []

        with patch("locallm.core.router.calculate_vram_breakdown") as mock_vram:
            # Candidate 70B model fails VRAM fit
            mock_vram.return_value = VRAMSizingResult(
                model_weights_gb=40.0,
                kv_cache_gb=4.0,
                cuda_overhead_gb=0.6,
                total_vram_gb=44.6,
                usable_vram_gb=10.0,
                headroom_gb=-34.6,
                is_fit=False,
                status="SPILLOVER",
                status_message="Spillover",
                max_context_tokens=2048,
                context_tokens=8192,
                bytes_per_token=524288,
            )
            route = route_prompt(
                "Prove step-by-step why P != NP in complexity theory.",
                self.config,
                mock_client,
            )
            # Must stay on gemma4:12b due to VRAM safety guard!
            self.assertEqual(route.selected_model, "gemma4:12b")
            self.assertFalse(route.is_swapped)
            self.assertIn("exceeds VRAM, safely retained", route.reason)

    def test_route_prompt_test_pertanyaan_scenarios(self):
        """Verify routing for casual chat, heavy reasoning, tool schema, and summarization."""
        mock_client = MagicMock()
        mock_client.list_models.return_value = [
            {"name": "hermes3:latest", "size": 4 * 1024**3},
            {"name": "qwen3.5:9b", "size": 6 * 1024**3},
            {"name": "gemma4:12b-it-qat", "size": 7 * 1024**3},
        ]
        mock_client.get_loaded_models.return_value = ["hermes3:latest"]

        def mock_features(name: str):
            if "qwen" in name:
                return ["Tools", "Vision", "Reasoning"]
            if "gemma" in name:
                return ["Tools", "Vision", "Reasoning"]
            return ["Tools"]

        mock_client.get_model_features.side_effect = mock_features
        mock_client.get_model_architecture_info.return_value = {
            "layers": 32,
            "kv_heads": 8,
            "head_dim": 128,
            "context_length": 32768,
        }

        with patch("locallm.core.router.calculate_vram_breakdown") as mock_vram:
            mock_vram.return_value = VRAMSizingResult(
                model_weights_gb=6.0,
                kv_cache_gb=1.5,
                cuda_overhead_gb=0.6,
                total_vram_gb=8.1,
                usable_vram_gb=10.0,
                headroom_gb=1.9,
                is_fit=True,
                status="100% GPU",
                status_message="Fit",
                max_context_tokens=32768,
                context_tokens=8192,
                bytes_per_token=131072,
            )

            # Test 1: Casual chat / analogy -> hermes3
            p1 = "Bro, lagi males banget mikir teknis nih. Kasih analogi santai dong warung makan."
            r1 = route_prompt(p1, self.config, mock_client)
            self.assertEqual(r1.task_type, TaskType.FAST_CHAT)
            self.assertEqual(r1.selected_model, "hermes3:latest")

            # Test 2: Algorithmic scheduling -> qwen3.5:9b
            p2 = "Ada 5 task (A, B, C, D, E) dengan durasi eksekusi [3, 1, 4, 2, 5] detik. Buktikan timeline eksekusinya."
            r2 = route_prompt(p2, self.config, mock_client)
            self.assertEqual(r2.task_type, TaskType.REASONING)
            self.assertEqual(r2.selected_model, "qwen3.5:9b")

            # Test 3: Structured tool calling & schema extraction -> gemma4:12b-it-qat
            p3 = "Ekstrak data log error berikut ke dalam schema JSON murni untuk pemanggilan tool trigger_incident_alert"
            r3 = route_prompt(p3, self.config, mock_client)
            self.assertEqual(r3.task_type, TaskType.TOOLS)
            self.assertEqual(r3.selected_model, "gemma4:12b-it-qat")

            # Test 4: Summarization / bullet points -> hermes3
            # Simulate loaded model is currently qwen3.5:9b
            mock_client.get_loaded_models.return_value = ["qwen3.5:9b"]
            p4 = "Ringkas poin kendala teknis berikut jadi 3 bullet points pendek tanpa basa-basi."
            r4 = route_prompt(p4, self.config, mock_client)
            self.assertEqual(r4.task_type, TaskType.FAST_CHAT)
            self.assertEqual(r4.selected_model, "hermes3:latest")

            # Test 5: Follow-up file creation in folder path -> retains gemma4:12b-it-qat (never downgrades to hermes3)
            mock_client.get_loaded_models.return_value = ["gemma4:12b-it-qat"]
            history_t5 = [
                {"role": "user", "content": "Buat architecture modular yang scalable untuk banyak project"},
                {"role": "assistant", "content": "Berikut arsitekturnya:\n```python\nclass Config: pass\n```\n├── config.py\n└── main.py"},
            ]
            p5 = "bisa gak kamu buatkan filenya di folder ini C:\\Users\\mfath\\Downloads\\Bot Signal"
            r5 = route_prompt(p5, self.config, mock_client, history=history_t5)
            self.assertEqual(r5.task_type, TaskType.TOOLS)
            self.assertEqual(r5.selected_model, "gemma4:12b-it-qat")
            self.assertFalse(r5.is_swapped)

    def test_route_prompt_coder_parameter_hierarchy_and_vram_fallback(self):
        """Verify that multiple coder models are prioritized by parameter size, with VRAM fallback."""
        mock_client = MagicMock()
        mock_client.list_models.return_value = [
            {"name": "gemma4:12b", "size": 7 * 1024**3},
            {"name": "qwen2.5-coder:14b", "size": 9 * 1024**3},
            {"name": "qwen2.5-coder:7b", "size": 4 * 1024**3},
        ]
        mock_client.get_loaded_models.return_value = ["gemma4:12b"]
        mock_client.get_model_features.return_value = ["Tools"]

        # Scenario A: Both 14b and 7b fit in VRAM -> 14b is selected due to higher parameter size
        with patch("locallm.core.router.check_model_vram_fit", return_value=True):
            prompt = "Bisa buatkan script python bot di folder ini C:\\Users\\mfath\\Downloads\\Bot Signal"
            route = route_prompt(prompt, self.config, mock_client)
            self.assertEqual(route.selected_model, "qwen2.5-coder:14b")
            self.assertEqual(route.task_type, TaskType.TOOLS)
            self.assertIn("Specialist Coding Agent", route.reason)

        # Scenario B: 14b exceeds VRAM, but 7b fits -> falls back to 7b seamlessly
        def mock_vram_fit(model_name, *args, **kwargs):
            return "14b" not in model_name

        with patch("locallm.core.router.check_model_vram_fit", side_effect=mock_vram_fit):
            prompt = "Bisa buatkan script python bot di folder ini C:\\Users\\mfath\\Downloads\\Bot Signal"
            route = route_prompt(prompt, self.config, mock_client)
            self.assertEqual(route.selected_model, "qwen2.5-coder:7b")
            self.assertEqual(route.task_type, TaskType.TOOLS)
            self.assertIn("Specialist Coding Agent", route.reason)

    def test_is_match_negated_detection(self):
        """Test clause-proximity negation detection with double-negative resilience."""
        # Simple negation
        s1 = "Tolong jelaskan konsep SQL, jangan bikin file ya"
        self.assertTrue(is_match_negated(s1, s1.find("bikin file")))

        # Double negative idiom: jangan lupa (positive intent)
        s2 = "jangan lupa buatkan file config.json ya"
        self.assertFalse(is_match_negated(s2, s2.find("buatkan file")))

        # Multi-clause with comma boundary
        s3 = "aku nggak mau cara lama, tolong buatkan script baru"
        self.assertFalse(is_match_negated(s3, s3.find("buatkan script")))

        # English negation
        s4 = "explain docker containers, don't run any commands"
        self.assertTrue(is_match_negated(s4, s4.find("run")))

    def test_classify_prompt_negation_guard(self):
        """Prompt with negated tool or coding intent should not be categorized as TOOLS or CODING."""
        # 1. Negated tool action
        p1 = "Tolong jelaskan konsep SQL database, jangan bikin file dan jangan jalankan script ya"
        task1, tier1, _ = classify_prompt(p1)
        self.assertNotEqual(task1, TaskType.TOOLS)

        # 2. Negated coding action
        p2 = "bikinin rangkuman artikel aja, nggak usah coding ya"
        task2, tier2, _ = classify_prompt(p2)
        self.assertNotEqual(task2, TaskType.CODING)

        # 3. Double negative positive tool intent
        p3 = "jangan lupa buatkan file config.json ya"
        task3, tier3, _ = classify_prompt(p3)
        self.assertEqual(task3, TaskType.TOOLS)


if __name__ == "__main__":
    unittest.main()

